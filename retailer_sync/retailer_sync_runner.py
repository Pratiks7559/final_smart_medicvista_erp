"""
retailer_sync_runner.py
-----------------------
Background sync loop. Talks to wholesaler API only.
All MySQL writes go through SyncBridge → app_db (your existing DB class).
SQLite is used ONLY for the offline status-update queue.
"""

import sys
import time
import logging
import json
import os
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent / 'retailer_sync_config.json'
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Copy retailer_sync_config.template.json to retailer_sync_config.json "
            "and fill in your values."
        )
    with open(config_path, 'r', encoding='utf-8') as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith('_comment')}


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(log_file: str, level=logging.INFO):
    fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8'),
    ]
    logging.basicConfig(level=level, format=fmt, handlers=handlers)
    return logging.getLogger('retailer_sync')


# ---------------------------------------------------------------------------
# Sync runner
# ---------------------------------------------------------------------------

class RetailerSyncRunner:
    def __init__(self, config: dict, on_sync_complete=None):
        self.config             = config
        self.retailer_id        = config['retailer_id']
        self.sync_interval      = config.get('sync_interval_seconds', 60)
        self.on_sync_complete   = on_sync_complete

        from retailer_sync_service import RequestSyncService
        from retailer_sync_db import RetailerCacheDB

        self.service = RequestSyncService(
            server_url=config['server_url'],
            api_key=config['api_key'],
            timeout=config.get('request_timeout_seconds', 10),
        )
        # SQLite — offline queue only, no request rows stored here
        self.db = RetailerCacheDB(config.get('cache_db_file', 'retailer_sync_queue.db'))
        self.logger = logging.getLogger('retailer_sync')

        self._connected      = False
        self._last_sync_time = None
        self._stop_flag      = False
        self._wake_event     = __import__('threading').Event()

    # ------------------------------------------------------------------
    # Called by SyncBridge when user clicks Generate Report
    # ------------------------------------------------------------------

    def fetch_and_generate(self, wholesaler_request_id: int,
                           output_dir: str = 'retailer_reports') -> dict:
        """
        Full pipeline:
          1. Fetch report data JSON from wholesaler.
          2. Mark PROCESSING on wholesaler.
          3. Generate PDF + Excel locally.
          4. Mark COMPLETED or FAILED on wholesaler.

        MySQL status updates are handled by SyncBridge after this returns.

        Returns: {ok, pdf_path, excel_path, error}
        """
        from retailer_report_generator import ReportGenerator

        # Step 1 — fetch raw data from wholesaler
        fetch = self.service.get_request_data(wholesaler_request_id)
        if not fetch['ok']:
            self.logger.error(
                "fetch_and_generate: data fetch failed id=%s: %s",
                wholesaler_request_id, fetch['error'],
            )
            return {'ok': False, 'pdf_path': None, 'excel_path': None,
                    'error': fetch['error']}

        # Step 2 — tell wholesaler we are processing
        self._send_status(wholesaler_request_id, 'PROCESSING')

        # Step 3 — generate PDF + Excel from JSON data
        gen    = ReportGenerator(output_dir=output_dir)
        result = gen.generate(fetch)

        # Step 4 — tell wholesaler final status
        final = 'COMPLETED' if result['ok'] else 'FAILED'
        self._send_status(wholesaler_request_id, final)

        if result['ok']:
            self.logger.info(
                "fetch_and_generate: COMPLETED id=%s pdf=%s excel=%s",
                wholesaler_request_id, result['pdf_path'], result['excel_path'],
            )
        else:
            self.logger.error(
                "fetch_and_generate: FAILED id=%s error=%s",
                wholesaler_request_id, result['error'],
            )
        return result

    def _send_status(self, request_id: int, status: str):
        """
        Send status to wholesaler. If offline, queue for later.
        Does NOT touch retailer MySQL — SyncBridge handles that.
        """
        result = self.service.update_status(request_id, status)
        if result['ok']:
            self.logger.info("Status sent: id=%s → %s", request_id, status)
        else:
            self.logger.warning(
                "Wholesaler offline, queuing status: id=%s → %s", request_id, status
            )
            self.db.queue_status_update(request_id, status)

    # ------------------------------------------------------------------
    # Core sync cycle
    # ------------------------------------------------------------------

    def run_once(self):
        self.logger.info("--- Sync cycle start ---")
        new_requests = []
        error        = None

        conn_result      = self.service.test_connection()
        self._connected  = conn_result['connected']

        if not self._connected:
            error = conn_result['error']
            self.logger.warning(
                "Wholesaler unreachable [%s]: %s. Retry in %ds.",
                self.config['server_url'], error, self.sync_interval,
            )
            self._fire_callback(new_requests=[], error=error)
            return

        self.logger.info(
            "Connected [mode=%s server_time=%s]",
            conn_result.get('server_mode', '?'),
            conn_result.get('server_time', '?'),
        )

        # Flush offline queue first
        pending_queue = self.db.get_pending_updates()
        if pending_queue:
            self.logger.info("Flushing %d queued status updates...", len(pending_queue))
            self.service.sync_pending_updates(
                pending_queue,
                on_success=self._on_queue_success,
                on_fail=self._on_queue_fail,
            )

        # Fetch pending requests from wholesaler
        fetch_result = self.service.get_requests()
        if fetch_result['ok']:
            new_requests         = fetch_result['requests']
            self._last_sync_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.logger.info(
                "Fetched %d pending request(s). Last sync: %s",
                len(new_requests), self._last_sync_time,
            )
        else:
            error = fetch_result['error']
            self.logger.error("Failed to fetch requests: %s", error)

        self._fire_callback(new_requests=new_requests, error=error)
        self.logger.info("--- Sync cycle end ---")

    def _fire_callback(self, new_requests: list, error):
        if self.on_sync_complete:
            try:
                self.on_sync_complete({
                    'connected':      self._connected,
                    'last_sync_time': self._last_sync_time,
                    'new_requests':   new_requests,
                    'error':          error,
                })
            except Exception:
                self.logger.exception("Error in on_sync_complete callback")

    def force_wake(self):
        """Called by SyncBridge.force_sync_now() — interrupts current sleep immediately."""
        self._wake_event.set()

    def run_forever(self):
        self.logger.info(
            "Sync runner started. Server: %s | Interval: %ds",
            self.config['server_url'], self.sync_interval,
        )
        self._stop_flag = False
        self._wake_event.clear()
        while not self._stop_flag:
            try:
                self.run_once()
            except Exception:
                self.logger.exception("Unexpected error in sync cycle — continuing.")
            self._wake_event.wait(timeout=self.sync_interval)
            self._wake_event.clear()
        self.logger.info("Sync runner stopped.")

    def stop(self):
        self._stop_flag = True
        self._wake_event.set()   # unblock wait() immediately

    def _on_queue_success(self, queue_id: int, request_id: int, new_status: str):
        self.db.remove_pending_update(queue_id)
        self.logger.info("Flushed queued update: id=%s → %s", request_id, new_status)

    def _on_queue_fail(self, queue_id: int):
        self.db.increment_attempt(queue_id)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Retailer sync runner')
    parser.add_argument('--config',    default=None)
    parser.add_argument('--once',      action='store_true')
    parser.add_argument('--test-conn', action='store_true')
    parser.add_argument('--status',    nargs=2, metavar=('REQUEST_ID', 'NEW_STATUS'))
    args = parser.parse_args()

    config = _load_config(args.config)
    _setup_logging(
        config.get('log_file', 'retailer_sync.log'),
        level=logging.DEBUG if os.getenv('SYNC_DEBUG') else logging.INFO,
    )

    runner = RetailerSyncRunner(config)

    if args.test_conn:
        result = runner.service.test_connection()
        if result['connected']:
            print(f"[OK] Connected  |  Mode: {result['server_mode']}  |  Server time: {result['server_time']}")
        else:
            print(f"[FAIL] Disconnected  |  Error: {result['error']}")
        sys.exit(0 if result['connected'] else 1)

    if args.status:
        request_id, new_status = int(args.status[0]), args.status[1].upper()
        runner._send_status(request_id, new_status)
        sys.exit(0)

    if args.once:
        runner.run_once()
        sys.exit(0)

    runner.run_forever()


if __name__ == '__main__':
    main()
