"""
setup_retailers.py
------------------
Creates all 4 retailers in wholesaler database with proper API keys.

Usage:
    python manage.py shell < setup_retailers.py
    
Or:
    python setup_retailers.py
"""

import os
import sys
import django

# Django setup
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.retailer_models import RetailerMaster, RetailerSession

# Retailer data - MUST match application.py _RETAILER_MAP exactly
RETAILERS = [
    {
        'retailer_id': 1,
        'retailer_name': 'BSL Pharmacy',
        'retailer_code': 'RTL001',
        'api_key': 'qAbkplyh1aezY0FAUkYv0rVMIshlIl9CVsR35eqzwGo',
        'is_active': True,
    },
    {
        'retailer_id': 2,
        'retailer_name': 'MedPlus Retail',
        'retailer_code': 'RTL002',
        'api_key': 'xYz9mN3pLq2wRt8vB5nK7cF1dG4hJ6sA0eU2iO9lP3',
        'is_active': True,
    },
    {
        'retailer_id': 3,
        'retailer_name': 'Apollo Pharmacy',
        'retailer_code': 'RTL003',
        'api_key': 'aB1cD2eF3gH4iJ5kL6mN7oP8qR9sT0uV1wX2yZ3aC4',
        'is_active': True,
    },
    {
        'retailer_id': 4,
        'retailer_name': 'Wellness Forever',
        'retailer_code': 'RTL004',
        'api_key': 'bC2dE3fG4hI5jK6lM7nO8pQ9rS0tU1vW2xY3zA4bC5',
        'is_active': True,
    },
]


def create_retailers():
    """Create or update all retailers."""
    created_count = 0
    updated_count = 0
    
    for data in RETAILERS:
        retailer, created = RetailerMaster.objects.update_or_create(
            retailer_id=data['retailer_id'],
            defaults={
                'retailer_name': data['retailer_name'],
                'retailer_code': data['retailer_code'],
                'api_key': data['api_key'],
                'is_active': data['is_active'],
            }
        )
        
        # Create session record
        RetailerSession.objects.get_or_create(
            retailer=retailer,
            defaults={'is_online': False}
        )
        
        if created:
            created_count += 1
            print(f"[+] Created: {retailer.retailer_name} ({retailer.retailer_code}) - API Key: {retailer.api_key[:20]}...")
        else:
            updated_count += 1
            print(f"[*] Updated: {retailer.retailer_name} ({retailer.retailer_code}) - API Key: {retailer.api_key[:20]}...")
    
    print(f"\n{'='*60}")
    print(f"Total: {created_count} created, {updated_count} updated")
    print(f"{'='*60}\n")
    
    # Display all retailers
    print("Current Retailers in Database:")
    print(f"{'ID':<5} {'Name':<25} {'Code':<10} {'API Key':<30} {'Status':<10}")
    print("-" * 90)
    
    for r in RetailerMaster.objects.all().order_by('retailer_id'):
        status = "Active" if r.is_active else "Inactive"
        api_preview = r.api_key[:20] + "..." if len(r.api_key) > 20 else r.api_key
        print(f"{r.retailer_id:<5} {r.retailer_name:<25} {r.retailer_code:<10} {api_preview:<30} {status:<10}")


if __name__ == '__main__':
    print("Setting up retailers in wholesaler database...\n")
    create_retailers()
    print("\n[OK] Setup complete!")
