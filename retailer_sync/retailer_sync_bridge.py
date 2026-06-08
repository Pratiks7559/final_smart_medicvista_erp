"""
retailer_sync_bridge.py
-----------------------
Thread-safe bridge between RetailerSyncRunner (background thread)
and the Tkinter application (main thread).

Responsibilities
----------------
- Owns the background sync thread.
- After every sync cycle: writes new requests into retailer MySQL.
- Provides push_status_update() and force_sync_now() for button handlers.
- All Tkinter widget updates scheduled via root.after() — never from thread.

Status vocabulary alignment
----------------------------
Wholesaler API sends:  PENDING / PROCESSING / COMPLETED / FAILED  (uppercase)
Retailer MySQL stores: Pending / Processing / Completed / Failed   (capitalised)
Retailer screen tags:  Pending / Processing / Processed / Failed

This bridge converts wholesaler uppercase → capitalised before writing MySQL.
"COMPLETED" → "Processed"  to match your existing screen tag and
mark_request_processed() which sets status = 'Processed'.
"""

import threading
import logging
from retailer_sync_runner import RetailerSyncRunner

logger = logging.getLogger('retailer_sync')

# Wholesaler uppercase → retailer MySQL capitalised
_STATUS_MAP = {
    'PENDING':    'Pending',
    'PROCESSING': 'Processing',
    'COMPLETED':  'Processed',   # matches your existing screen tag + mark_request_processed
    'FAILED':     'Failed',
}


class SyncBridge:
    def __init__(self, tk_root, config: dict, app_db):
        """
        Parameters
        ----------
        tk_root : tk.Tk
        config  : dict from _load_config()
        app_db  : your existing DB class instance (has upsert_wholesaler_requests,
                  update_request_status_by_reference)
        """
        self._root   = tk_root
        self._config = config
        self._app_db = app_db
        self._lock   = threading.Lock()
        self.on_update = None   # set to on_show() after construction

        self._runner = RetailerSyncRunner(
            config=config,
            on_sync_complete=self._thread_callback,
        )
        self._thread = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._runner.run_forever,
            name='RetailerSyncThread',
            daemon=True,
        )
        self._thread.start()
        logger.info("SyncBridge started — polling every %ds",
                    self._config.get('sync_interval_seconds', 60))

    def stop(self):
        self._runner.stop()
        if self._thread:
            self._thread.join(timeout=3)
        logger.info("SyncBridge stopped.")

    # ------------------------------------------------------------------
    # Button handlers — called from main thread
    # ------------------------------------------------------------------

    def force_sync_now(self):
        """Sync Now button — triggers immediate cycle, non-blocking."""
        threading.Thread(
            target=self._runner.run_once,
            daemon=True,
            name='SyncForceThread',
        ).start()

    def push_status_update(self, reference_id: int, wholesaler_status: str):
        """
        Mark Processed button.
        Sends status to wholesaler API and updates retailer MySQL.
        Runs in short thread so UI stays responsive.

        reference_id    : the wholesaler request_id stored in your reference_id column
        wholesaler_status: 'COMPLETED' / 'FAILED' / 'PROCESSING'  (uppercase)
        """
        retailer_id   = self._config['retailer_id']
        mysql_status  = _STATUS_MAP.get(wholesaler_status.upper(), wholesaler_status.capitalize())

        def _do():
            # Send to wholesaler
            self._runner._send_status(reference_id, wholesaler_status.upper())
            # Update retailer MySQL
            try:
                self._app_db.update_request_status_by_reference(
                    reference_id, mysql_status, retailer_id
                )
                logger.info("MySQL updated: ref=%s → %s", reference_id, mysql_status)
            except Exception:
                logger.exception("MySQL update failed: ref=%s", reference_id)
            # Refresh UI on main thread
            if self.on_update:
                self._root.after(0, lambda: self.on_update({}))

        threading.Thread(target=_do, daemon=True, name='SyncPushThread').start()

    def generate_report(self, reference_id: int, output_dir: str = 'retailer_reports'):
        """
        Generate Report button.
        Fetches data from wholesaler, generates PDF + Excel, updates MySQL.
        Runs in thread. Returns immediately — result delivered via on_generate_done.

        Caller must set on_generate_done before calling.
        Signature: on_generate_done(reference_id, result_dict)
        """
        retailer_id = self._config['retailer_id']

        def _do():
            # Full pipeline — fetch data → generate files → update wholesaler status
            result = self._runner.fetch_and_generate(
                wholesaler_request_id=reference_id,
                output_dir=output_dir,
            )
            # Update retailer MySQL based on outcome
            mysql_status = 'Processed' if result['ok'] else 'Failed'
            try:
                self._app_db.update_request_status_by_reference(
                    reference_id, mysql_status, retailer_id
                )
            except Exception:
                logger.exception("MySQL status update failed after generate: ref=%s", reference_id)

            # Deliver result to main thread
            if self.on_generate_done:
                self._root.after(0, lambda: self.on_generate_done(reference_id, result))
            if self.on_update:
                self._root.after(0, lambda: self.on_update({}))

        threading.Thread(target=_do, daemon=True, name='GenerateReportThread').start()

    # ------------------------------------------------------------------
    # Internal — background thread → main thread
    # ------------------------------------------------------------------

    def _thread_callback(self, result: dict):
        """
        Called from background thread after every sync cycle.
        Writes new requests into retailer MySQL then schedules UI refresh.
        NEVER touch Tkinter here.
        """
        new_requests = result.get('new_requests', [])
        if new_requests:
            retailer_id = self._config['retailer_id']
            try:
                count = self._app_db.upsert_wholesaler_requests(
                    new_requests, retailer_id
                )
                logger.info("Wrote %d new request(s) into retailer MySQL.", count)
            except Exception:
                logger.exception("Failed writing requests to retailer MySQL.")

        with self._lock:
            self._last_result = result

        if self.on_update:
            self._root.after(0, lambda: self.on_update(result))
