import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from django.test import RequestFactory
from core.financial_views import export_financial_excel, export_financial_pdf
from core.models import Web_User

print("=" * 70)
print("WEB EXPORT SIMULATION TEST")
print("=" * 70)

# Get or create a test user
user = Web_User.objects.first()
if not user:
    print("\nNo user found! Creating test user...")
    user = Web_User.objects.create_user('testuser', 'test@test.com', 'password')

print(f"\nUsing user: {user.username}")

# Create request factory
factory = RequestFactory()

# Test 1: Excel Export WITHOUT filters
print("\n" + "=" * 70)
print("TEST 1: Excel Export WITHOUT Filters")
print("=" * 70)

request = factory.get('/export-financial-excel/')
request.user = user

try:
    response = export_financial_excel(request)
    
    if response.status_code == 200:
        content_length = len(response.content)
        print(f"SUCCESS: Excel export successful!")
        print(f"  File size: {content_length} bytes")
        
        # Save to file
        with open('web_test_export_no_filter.xlsx', 'wb') as f:
            f.write(response.content)
        print(f"  Saved as: web_test_export_no_filter.xlsx")
        
        if content_length < 6000:
            print(f"  WARNING: File size is small - might have no data!")
    else:
        print(f"FAILED: Excel export failed with status: {response.status_code}")
        
except Exception as e:
    print(f"ERROR: Excel export error: {e}")
    import traceback
    traceback.print_exc()

# Test 2: Excel Export WITH date filter
print("\n" + "=" * 70)
print("TEST 2: Excel Export WITH Date Filter (16-03-2026)")
print("=" * 70)

request = factory.get('/export-financial-excel/?start_date=2026-03-16&end_date=2026-03-16')
request.user = user

try:
    response = export_financial_excel(request)
    
    if response.status_code == 200:
        content_length = len(response.content)
        print(f"SUCCESS: Excel export successful!")
        print(f"  File size: {content_length} bytes")
        
        # Save to file
        with open('web_test_export_with_filter.xlsx', 'wb') as f:
            f.write(response.content)
        print(f"  Saved as: web_test_export_with_filter.xlsx")
        
        if content_length < 6000:
            print(f"  WARNING: File size is small - might have no data!")
    else:
        print(f"FAILED: Excel export failed with status: {response.status_code}")
        
except Exception as e:
    print(f"ERROR: Excel export error: {e}")
    import traceback
    traceback.print_exc()

# Test 3: PDF Export WITHOUT filters
print("\n" + "=" * 70)
print("TEST 3: PDF Export WITHOUT Filters")
print("=" * 70)

request = factory.get('/export-financial-pdf/')
request.user = user

try:
    response = export_financial_pdf(request)
    
    if response.status_code == 200:
        content_length = len(response.content)
        print(f"SUCCESS: PDF export successful!")
        print(f"  File size: {content_length} bytes")
        
        # Save to file
        with open('web_test_export_no_filter.pdf', 'wb') as f:
            f.write(response.content)
        print(f"  Saved as: web_test_export_no_filter.pdf")
        
        if content_length < 3000:
            print(f"  WARNING: File size is small - might have no data!")
    else:
        print(f"FAILED: PDF export failed with status: {response.status_code}")
        
except Exception as e:
    print(f"ERROR: PDF export error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: PDF Export WITH date filter
print("\n" + "=" * 70)
print("TEST 4: PDF Export WITH Date Filter (16-03-2026)")
print("=" * 70)

request = factory.get('/export-financial-pdf/?start_date=2026-03-16&end_date=2026-03-16')
request.user = user

try:
    response = export_financial_pdf(request)
    
    if response.status_code == 200:
        content_length = len(response.content)
        print(f"SUCCESS: PDF export successful!")
        print(f"  File size: {content_length} bytes")
        
        # Save to file
        with open('web_test_export_with_filter.pdf', 'wb') as f:
            f.write(response.content)
        print(f"  Saved as: web_test_export_with_filter.pdf")
        
        if content_length < 3000:
            print(f"  WARNING: File size is small - might have no data!")
    else:
        print(f"FAILED: PDF export failed with status: {response.status_code}")
        
except Exception as e:
    print(f"ERROR: PDF export error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("\nGenerated files:")
print("  - web_test_export_no_filter.xlsx")
print("  - web_test_export_with_filter.xlsx")
print("  - web_test_export_no_filter.pdf")
print("  - web_test_export_with_filter.pdf")
print("\nOpen these files and check if data is visible.")
print("\nIf data is missing in filtered exports, the issue is with date filtering.")
print("=" * 70)
