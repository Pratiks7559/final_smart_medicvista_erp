"""
retailer_tk_panel.py
--------------------
Drop-in Tkinter Frame widget for the Retailer Report Request panel.

Embed in ANY existing Tkinter window with two lines:

    from retailer_tk_panel import ReportRequestPanel
    panel = ReportRequestPanel(some_frame_or_window, config)
    panel.pack(fill='both', expand=True)

The panel manages its own SyncBridge internally.
It does NOT require any changes to existing Tkinter code.

Features
--------
- Connection status indicator (green/red dot + last sync time)
- Live request table (auto-refreshes after every sync cycle)
- "Sync Now" button for immediate manual refresh
- "Mark Processing / Completed / Failed" buttons per selected row
- Offline-safe: shows cached data when server is unavailable
- Clean shutdown when parent window closes
"""

import tkinter as tk
from tkinter import ttk, messagebox
import logging
from pathlib import Path

logger = logging.getLogger('retailer_sync')


# Colours — adjust to match your existing Tkinter theme
_CLR_CONNECTED    = '#16a34a'   # green
_CLR_DISCONNECTED = '#dc2626'   # red
_CLR_CHECKING     = '#d97706'   # amber
_CLR_BG           = '#f9fafb'
_CLR_HEADER       = '#4a4e69'

_STATUS_COLORS = {
    'PENDING':    '#92400e',
    'PROCESSING': '#1e40af',
    'COMPLETED':  '#065f46',
    'FAILED':     '#991b1b',
}
_STATUS_BG = {
    'PENDING':    '#fef3c7',
    'PROCESSING': '#dbeafe',
    'COMPLETED':  '#d1fae5',
    'FAILED':     '#fee2e2',
}


class ReportRequestPanel(tk.Frame):
    """
    Self-contained panel widget.  Drop into any Frame or Toplevel.

    Parameters
    ----------
    parent : tk.Widget
        Parent widget (Frame, Notebook tab, Toplevel, etc.)
    config : dict
        Loaded from retailer_sync_config.json
    """

    def __init__(self, parent, config: dict, **kwargs):
        super().__init__(parent, bg=_CLR_BG, **kwargs)
        self._config = config
        self._bridge = None
        self._build_ui()
        self._start_bridge()
        # Register clean shutdown on root window close
        self._find_root().protocol('WM_DELETE_WINDOW', self._on_close)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ── Header row ──────────────────────────────────────────────
        header = tk.Frame(self, bg=_CLR_BG, padx=12, pady=8)
        header.pack(fill='x')

        tk.Label(
            header, text='Retailer Report Requests',
            font=('Segoe UI', 13, 'bold'), fg=_CLR_HEADER, bg=_CLR_BG,
        ).pack(side='left')

        # Sync Now button
        self._btn_sync = tk.Button(
            header, text='⟳  Sync Now',
            command=self._on_sync_now,
            font=('Segoe UI', 9), relief='flat',
            bg='#e0e7ff', fg='#3730a3', cursor='hand2', padx=8, pady=3,
        )
        self._btn_sync.pack(side='right', padx=(4, 0))

        # ── Status bar ──────────────────────────────────────────────
        status_bar = tk.Frame(self, bg='#e5e7eb', padx=12, pady=6)
        status_bar.pack(fill='x')

        self._dot = tk.Label(status_bar, text='●', font=('Segoe UI', 11),
                             fg=_CLR_CHECKING, bg='#e5e7eb')
        self._dot.pack(side='left')

        self._lbl_conn = tk.Label(
            status_bar, text='Connecting…',
            font=('Segoe UI', 9), fg='#374151', bg='#e5e7eb',
        )
        self._lbl_conn.pack(side='left', padx=(4, 16))

        self._lbl_sync = tk.Label(
            status_bar, text='', font=('Segoe UI', 8), fg='#6b7280', bg='#e5e7eb',
        )
        self._lbl_sync.pack(side='left')

        tk.Label(
            status_bar,
            text=f"Server: {self._config.get('server_url', '?')}  "
                 f"[{self._config.get('server_mode', 'LOCAL')}]",
            font=('Segoe UI', 8), fg='#9ca3af', bg='#e5e7eb',
        ).pack(side='right')

        # ── Request table ───────────────────────────────────────────
        table_frame = tk.Frame(self, bg=_CLR_BG, padx=12, pady=8)
        table_frame.pack(fill='both', expand=True)

        columns = ('request_id', 'request_type', 'from_date', 'to_date', 'status', 'sync_time')
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show='headings',
            selectmode='browse', height=12,
        )

        col_cfg = [
            ('request_id',   'ID',          60),
            ('request_type', 'Report Type', 110),
            ('from_date',    'From',        95),
            ('to_date',      'To',          95),
            ('status',       'Status',      100),
            ('sync_time',    'Last Synced', 145),
        ]
        for col, heading, width in col_cfg:
            self._tree.heading(col, text=heading,
                               command=lambda c=col: self._sort_column(c))
            self._tree.column(col, width=width, anchor='center')

        # Scrollbar
        vsb = ttk.Scrollbar(table_frame, orient='vertical', command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Status-colour row tags
        for status, bg in _STATUS_BG.items():
            self._tree.tag_configure(status, background=bg,
                                     foreground=_STATUS_COLORS.get(status, '#000'))

        # ── Action buttons ──────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=_CLR_BG, padx=12, pady=6)
        btn_frame.pack(fill='x')

        tk.Label(btn_frame, text='Selected request:',
                 font=('Segoe UI', 9), fg='#6b7280', bg=_CLR_BG).pack(side='left')

        for label, status, bg, fg in [
            ('▶ Mark Processing', 'PROCESSING', '#dbeafe', '#1e40af'),
            ('✔ Mark Completed',  'COMPLETED',  '#d1fae5', '#065f46'),
            ('✘ Mark Failed',     'FAILED',     '#fee2e2', '#991b1b'),
        ]:
            tk.Button(
                btn_frame, text=label,
                command=lambda s=status: self._on_mark_status(s),
                font=('Segoe UI', 9), relief='flat',
                bg=bg, fg=fg, cursor='hand2', padx=8, pady=3,
            ).pack(side='left', padx=(8, 0))

        # ── Error label ─────────────────────────────────────────────
        self._lbl_error = tk.Label(
            self, text='', font=('Segoe UI', 8),
            fg='#dc2626', bg=_CLR_BG, padx=12, anchor='w',
        )
        self._lbl_error.pack(fill='x')

    # ------------------------------------------------------------------
    # Bridge lifecycle
    # ------------------------------------------------------------------

    def _start_bridge(self):
        from retailer_sync_bridge import SyncBridge
        self._bridge = SyncBridge(self._find_root(), self._config)
        self._bridge.on_update = self._on_sync_result   # main-thread callback
        self._bridge.start()

    def _find_root(self):
        w = self
        while w.master:
            w = w.master
        return w

    # ------------------------------------------------------------------
    # Sync result handler — always called on MAIN THREAD via after()
    # ------------------------------------------------------------------

    def _on_sync_result(self, result: dict):
        connected = result.get('connected', False)
        last_sync  = result.get('last_sync_time')
        error      = result.get('error')

        # Update status indicator
        if connected:
            self._dot.config(fg=_CLR_CONNECTED)
            self._lbl_conn.config(text='Connected')
        else:
            self._dot.config(fg=_CLR_DISCONNECTED)
            self._lbl_conn.config(text='Disconnected')

        self._lbl_sync.config(
            text=f'Last sync: {last_sync}' if last_sync else 'Not synced yet'
        )
        self._lbl_error.config(text=f'Error: {error}' if error else '')

        # Refresh table from local cache (works even offline)
        self._refresh_table()

    def _refresh_table(self):
        rows = self._bridge.get_cached_requests()
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            status = r.get('status', 'PENDING')
            self._tree.insert('', 'end', iid=str(r['request_id']), values=(
                r['request_id'],
                r['request_type'],
                r['from_date'],
                r['to_date'],
                status,
                r.get('sync_time', ''),
            ), tags=(status,))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _on_sync_now(self):
        self._btn_sync.config(state='disabled', text='Syncing…')
        self._dot.config(fg=_CLR_CHECKING)
        self._lbl_conn.config(text='Connecting…')

        def _restore():
            self._btn_sync.config(state='normal', text='⟳  Sync Now')

        self._bridge.force_sync_now()
        # Restore button after 3 seconds regardless of result
        self.after(3000, _restore)

    def _on_mark_status(self, new_status: str):
        selected = self._tree.selection()
        if not selected:
            messagebox.showwarning('No Selection', 'Please select a request row first.')
            return
        request_id = int(selected[0])

        # Confirm
        row_vals = self._tree.item(selected[0], 'values')
        current_status = row_vals[4] if len(row_vals) > 4 else '?'

        ok = messagebox.askyesno(
            'Confirm Status Update',
            f'Request #{request_id}\n'
            f'Current: {current_status}  →  New: {new_status}\n\n'
            f'Confirm?',
        )
        if not ok:
            return

        self._bridge.push_status_update(request_id, new_status)
        # Optimistically update row colour immediately
        self._tree.item(selected[0], values=(
            row_vals[0], row_vals[1], row_vals[2], row_vals[3],
            new_status, row_vals[5],
        ), tags=(new_status,))

    def _sort_column(self, col):
        """Toggle sort on column header click."""
        items = [(self._tree.set(k, col), k) for k in self._tree.get_children('')]
        items.sort(reverse=getattr(self, f'_sort_{col}_rev', False))
        for index, (_, k) in enumerate(items):
            self._tree.move(k, '', index)
        setattr(self, f'_sort_{col}_rev', not getattr(self, f'_sort_{col}_rev', False))

    # ------------------------------------------------------------------
    # Clean shutdown
    # ------------------------------------------------------------------

    def _on_close(self):
        if self._bridge:
            self._bridge.stop()
        self._find_root().destroy()


# ---------------------------------------------------------------------------
# Standalone demo — run this file directly to test the panel
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import json, sys
    from pathlib import Path

    cfg_path = Path(__file__).parent / 'retailer_sync_config.json'
    if not cfg_path.exists():
        print(f"Config not found: {cfg_path}")
        print("Run retailer_sync_setup.py first.")
        sys.exit(1)

    with open(cfg_path, 'r') as f:
        raw = json.load(f)
    config = {k: v for k, v in raw.items() if not k.startswith('_comment')}

    # Set up logging so you can see sync output in terminal
    import logging, os
    from retailer_sync_runner import _setup_logging
    _setup_logging(config.get('log_file', 'retailer_sync.log'))

    root = tk.Tk()
    root.title(f"Retailer Sync Panel — {config.get('retailer_code', 'R?')}")
    root.geometry('800x500')
    root.configure(bg='#f9fafb')

    panel = ReportRequestPanel(root, config)
    panel.pack(fill='both', expand=True)

    root.mainloop()
