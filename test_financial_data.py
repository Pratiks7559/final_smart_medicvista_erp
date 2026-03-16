import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster, PurchaseMaster

# Check if data exists
sales_count = SalesMaster.objects.count()
purchase_count = PurchaseMaster.objects.count()

print(f"Total Sales: {sales_count}")
print(f"Total Purchases: {purchase_count}")

if sales_count > 0:
    print("\nFirst Sale:")
    sale = SalesMaster.objects.first()
    print(f"Date: {sale.sale_entry_date}")
    print(f"Product: {sale.product_name}")
    print(f"Quantity: {sale.sale_quantity}")

if purchase_count > 0:
    print("\nFirst Purchase:")
    purchase = PurchaseMaster.objects.first()
    print(f"Date: {purchase.purchase_entry_date}")
    print(f"Product: {purchase.product_name}")
    print(f"Quantity: {purchase.product_quantity}")
