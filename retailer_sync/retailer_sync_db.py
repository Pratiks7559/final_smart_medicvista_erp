"""
retailer_sync_db.py
-------------------
Manages the LOCAL SQLite file used ONLY for the offline status-update queue.

What lives here
---------------
pending_status_updates : status changes that could not be sent to the
                         wholesaler (server offline). Flushed automatically
                         on the next successful connection.

What does NOT live here
-----------------------
retailer_request rows  : written directly into retailer MySQL by
                         RetailerMySQLWriter (see retailer_sync_mysql.py).
report_data_cache      : written directly into retailer MySQL.

The SQLite file is intentionally minimal — it only exists to survive
situations where the retailer MySQL itself is temporarily unavailable
or the wholesaler cannot be reached.
"""

import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger('retailer_sync')


class RetailerCacheDB:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS pending_status_updates (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id      INTEGER NOT NULL,
                    new_status      TEXT NOT NULL,
                    queued_at       TEXT NOT NULL,
                    attempt_count   INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_pending_queued
                    ON pending_status_updates(queued_at);
            """)
        logger.debug("Offline queue DB initialised at %s", self.db_path)

    # ------------------------------------------------------------------
    # pending_status_updates — offline queue
    # ------------------------------------------------------------------

    def queue_status_update(self, request_id: int, new_status: str):
        """Queue a status update that could not reach the wholesaler."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM pending_status_updates WHERE request_id=?",
                (request_id,),
            )
            conn.execute(
                "INSERT INTO pending_status_updates "
                "(request_id, new_status, queued_at, attempt_count) VALUES (?,?,?,0)",
                (request_id, new_status, now),
            )
        logger.info("Queued offline status update: request_id=%s status=%s",
                    request_id, new_status)

    def get_pending_updates(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM pending_status_updates ORDER BY queued_at ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def increment_attempt(self, queue_id: int):
        with self._conn() as conn:
            conn.execute(
                "UPDATE pending_status_updates "
                "SET attempt_count = attempt_count + 1 WHERE id=?",
                (queue_id,),
            )

    def remove_pending_update(self, queue_id: int):
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM pending_status_updates WHERE id=?",
                (queue_id,),
            )
