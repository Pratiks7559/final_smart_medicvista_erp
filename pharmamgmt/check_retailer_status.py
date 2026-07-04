import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
sys.path.insert(0, r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt')
django.setup()

from django.apps import apps
from core.retailer_models import RetailerSession
from datetime import datetime, timedelta

model = apps.get_model('core', 'RetailerMaster')
r = model.objects.get(retailer_id=1)

print("=" * 60)
print("RETAILER STATUS CHECK")
print("=" * 60)
print(f"\nRetailer: {r.retailer_name}")
print(f"Retailer ID: {r.retailer_id}")
print(f"API Key: {r.api_key[:20]}...")
print(f"Is Active: {r.is_active}")

try:
    s = r.session
    print(f"\nSession Found: Yes")
    print(f"Last Seen: {s.last_seen}")
    print(f"Is Online: {s.is_online}")
    
    if s.last_seen:
        now = datetime.now()
        if s.last_seen.tzinfo is not None:
            from django.utils import timezone
            now = timezone.now()
        
        time_diff = now - s.last_seen
        seconds_ago = int(time_diff.total_seconds())
        print(f"Last seen {seconds_ago} seconds ago")
        
        if seconds_ago < 20:
            print("\n[OK] Retailer is ONLINE (last seen < 20 seconds)")
        else:
            print(f"\n[OFFLINE] Retailer is OFFLINE (last seen > 20 seconds)")
    else:
        print("\n[ERROR] last_seen is NULL")
        
except Exception as e:
    print(f"\nSession Error: {e}")
    print("Session may not exist for this retailer")

print("=" * 60)
