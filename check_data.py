import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster, PurchaseMaster, SupplierChallanMaster, CustomerChallanMaster

print("=== DATA CHECK ===")
print(f"Sales Count: {SalesMaster.objects.count()}")
print(f"Purchase Count: {PurchaseMaster.objects.count()}")
print(f"Customer Challan Count: {CustomerChallanMaster.objects.count()}")
print(f"Supplier Challan Count: {SupplierChallanMaster.objects.count()}")

print("\n=== SAMPLE SALES DATA ===")
sales = SalesMaster.objects.all()[:2]
for sale in sales:
    print(f"Date: {sale.sale_entry_date}, Product: {sale.product_name}, Qty: {sale.sale_quantity}")

print("\n=== SAMPLE PURCHASE DATA ===")
purchases = PurchaseMaster.objects.all()[:2]
for purchase in purchases:
    print(f"Date: {purchase.purchase_entry_date}, Product: {purchase.product_name}, Qty: {purchase.product_quantity}")
