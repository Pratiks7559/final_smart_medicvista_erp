# Retailer Sync Service

Standalone Python package that runs on each **retailer machine**.  
Pure Python stdlib — no pip installs required.

---

## Architecture

```
WHOLESALER ERP (Django)                    RETAILER MACHINE
─────────────────────────                  ────────────────────────────────
GET  /api/retailer/health/         ←───    RequestSyncService.test_connection()
GET  /api/retailer/pending-requests/ ←──  RequestSyncService.get_requests()
POST /api/retailer/update-status/  ←───   RequestSyncService.update_status()
                                           │
                                     RetailerSyncRunner (60-second loop)
                                           │
                                     RetailerCacheDB (SQLite)
                                     retailer_request_cache.db
```

---

## Files

| File | Purpose |
|------|---------|
| `retailer_sync_config.template.json` | Copy → `retailer_sync_config.json` and fill in |
| `retailer_sync_service.py` | `RequestSyncService` — all HTTP calls, LOCAL/CLOUD transparent |
| `retailer_sync_db.py` | `RetailerCacheDB` — SQLite local cache + offline queue |
| `retailer_sync_runner.py` | 60-second polling loop, offline retry, CLI entry point |
| `retailer_sync_setup.py` | Interactive first-time setup wizard |

---

## Quick Start

### 1. First-time setup (run once per machine)
```bash
cd retailer_sync
python retailer_sync_setup.py
```
This creates `retailer_sync_config.json` and tests the connection.

### 2. Start the sync service
```bash
python retailer_sync_runner.py
```

### 3. Test connection only
```bash
python retailer_sync_runner.py --test-conn
```

### 4. Single sync cycle (for testing)
```bash
python retailer_sync_runner.py --once
```

### 5. Push a status update manually
```bash
python retailer_sync_runner.py --status 42 COMPLETED
python retailer_sync_runner.py --status 42 FAILED
```

---

## Two Modes — Zero Code Changes

| Setting | LOCAL | CLOUD |
|---------|-------|-------|
| `server_mode` | `LOCAL` | `CLOUD` |
| `server_url` | `http://192.168.1.100:8000` | `https://erp.company.com` |

Only these two values in `retailer_sync_config.json` change.  
All code, all API paths, all logic remains identical.

---

## Offline Behaviour

- If the wholesaler server is unreachable, the sync runner logs a warning and skips the cycle.
- Status updates (COMPLETED / FAILED) that cannot be sent are saved in `pending_status_updates` table.
- On the next successful connection, the queue is flushed automatically before fetching new requests.
- The retailer can still see all previously cached requests even while offline.

---

## Extensible Request Types

Current types: `STOCK`, `PURCHASE`, `SALES`

Future types (no code changes needed):
`GST`, `PROFIT_LOSS`, `EXPIRY`, `CUSTOMER_LEDGER`, `SUPPLIER_LEDGER`, `CUSTOM_REPORT`

Types flow through as plain strings — the sync service never inspects them.

---

## Integrating with Existing Retailer Software

```python
from retailer_sync_runner import RetailerSyncRunner, _load_config, _setup_logging

config = _load_config()            # reads retailer_sync_config.json
_setup_logging(config['log_file'])
runner = RetailerSyncRunner(config)

# Start background thread
import threading
t = threading.Thread(target=runner.run_forever, daemon=True)
t.start()

# When report generation is done:
runner.push_status_update(request_id=42, new_status='COMPLETED')

# Read cached requests (works offline):
cached = runner.db.get_cached_by_status('PENDING')

# Check connection state for UI display:
state = runner.get_connection_status()
# {'connected': True, 'last_sync_time': '2025-01-15 10:30:00', ...}
```

---

## Security

- API key is the only credential stored. Never store wholesaler DB password.
- All communication is through REST API over HTTP (LOCAL) or HTTPS (CLOUD).
- Retailer never connects directly to wholesaler MySQL.
- HTTPS certificate validation is enforced in CLOUD mode automatically.
