"""
retailer_sync_setup.py
----------------------
Interactive first-time setup wizard for the retailer sync service.

Run once per retailer machine:
    python retailer_sync_setup.py

It will:
1. Ask for server mode, server URL, API key, retailer details.
2. Write retailer_sync_config.json.
3. Immediately test the connection and print result.
4. Print the command to start the sync runner.
"""

import json
import sys
from pathlib import Path


def _ask(prompt: str, default: str = '') -> str:
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    while True:
        value = input(f"{prompt}: ").strip()
        if value:
            return value
        print("  This field is required.")


def main():
    print("=" * 60)
    print("  Retailer Sync Service — First-Time Setup")
    print("=" * 60)
    print()

    print("Step 1: Server Mode")
    print("  LOCAL = wholesaler ERP is on the same LAN (http://)")
    print("  CLOUD = wholesaler ERP is on the internet (https://)")
    while True:
        mode = input("Server mode [LOCAL/CLOUD, default LOCAL]: ").strip().upper() or 'LOCAL'
        if mode in ('LOCAL', 'CLOUD'):
            break
        print("  Please enter LOCAL or CLOUD.")

    print()
    print("Step 2: Server URL (no trailing slash)")
    if mode == 'LOCAL':
        default_url = 'http://127.0.0.1:8000'
        print(f"  Example: http://192.168.1.100:8000")
    else:
        default_url = ''
        print("  Example: https://erp.yourcompany.com")
    server_url = _ask("Server URL", default_url)

    print()
    print("Step 3: API Key")
    print("  Find this in: Wholesaler Admin → RetailerMaster → your record → api_key")
    api_key = _ask("API Key")

    print()
    print("Step 4: Retailer ID")
    print("  Find this in: Wholesaler Admin → RetailerMaster → retailer_id column")
    while True:
        try:
            retailer_id = int(_ask("Retailer ID"))
            break
        except ValueError:
            print("  Must be a number.")

    print()
    retailer_code = _ask("Retailer Code (e.g. R1, R2)", "R1")

    print()
    sync_interval = input("Sync interval in seconds [60]: ").strip()
    sync_interval = int(sync_interval) if sync_interval.isdigit() else 60

    config = {
        "server_mode": mode,
        "server_url": server_url,
        "api_key": api_key,
        "retailer_id": retailer_id,
        "retailer_code": retailer_code,
        "sync_interval_seconds": sync_interval,
        "request_timeout_seconds": 10,
        "max_retry_attempts": 3,
        "log_file": "retailer_sync.log",
        "cache_db_file": "retailer_request_cache.db",
    }

    out_path = Path(__file__).parent / 'retailer_sync_config.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)
    print(f"\n✅ Config saved to: {out_path}")

    print("\nStep 5: Testing connection...")
    try:
        # Import after config is written so paths resolve correctly
        from retailer_sync_service import RequestSyncService
        svc = RequestSyncService(server_url=server_url, api_key=api_key, timeout=10)
        result = svc.test_connection()
        if result['connected']:
            print(f"  ✅ Connected!  Mode: {result['server_mode']}  Server time: {result['server_time']}")
        else:
            print(f"  ❌ Could not connect: {result['error']}")
            print("  Check the server URL and make sure the wholesaler ERP is running.")
    except ImportError:
        print("  (Skipped — retailer_sync_service.py not found in path)")

    print()
    print("=" * 60)
    print("Setup complete. To start the sync service:")
    print()
    print("  python retailer_sync_runner.py")
    print()
    print("Other useful commands:")
    print("  python retailer_sync_runner.py --test-conn")
    print("  python retailer_sync_runner.py --once")
    print("  python retailer_sync_runner.py --status <request_id> COMPLETED")
    print("=" * 60)


if __name__ == '__main__':
    main()
