import os
import sys
import django

sys.path.append(r'c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster

print("Checking SalesMaster records...")
sales = SalesMaster.objects.all()[:5]

for sale in sales:
    print(f"ID: {sale.id}, Product: {sale.product_name}, Qty: {sale.sale_quantity}, Free Qty: {sale.sale_free_qty}")

print("\nChecking if field exists in model...")
print("sale_free_qty field:", hasattr(SalesMaster, 'sale_free_qty'))

# Check actual field value
first_sale = SalesMaster.objects.first()
if first_sale:
    print(f"\nFirst sale free qty value: {first_sale.sale_free_qty}")
    print(f"Type: {type(first_sale.sale_free_qty)}")
