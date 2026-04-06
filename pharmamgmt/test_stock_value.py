import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import PurchaseMaster, SupplierChallanMaster, InventoryTransaction
from django.db.models import Sum, Max

# Find product
from core.models import ProductMaster
p = ProductMaster.objects.filter(product_name__icontains='1ST AID').first()
if not p:
    print("Product not found"); exit()

pid = p.productid
print(f"Product: {p.product_name} | ID: {pid}")

pm = PurchaseMaster.objects.filter(productid=pid)
print(f"\nPurchaseMaster rows: {pm.count()}")

sc = SupplierChallanMaster.objects.filter(product_id=pid)
print(f"SupplierChallanMaster rows: {sc.count()}")
for c in sc:
    print(f"  batch={c.product_batch_no} qty={c.product_quantity} mrp={c.product_mrp} free={c.product_free_qty}")

it = InventoryTransaction.objects.filter(product_id=pid)
print(f"InventoryTransaction rows: {it.count()}")
for t in it:
    print(f"  type={t.transaction_type} qty={t.quantity} mrp={t.mrp} rate={t.rate}")

# What MRP should be used
mrp_from_it = it.aggregate(m=Max('mrp'))['m'] or 0
mrp_from_sc = sc.aggregate(m=Max('product_mrp'))['m'] or 0
print(f"\nMRP from IT: {mrp_from_it}")
print(f"MRP from SC: {mrp_from_sc}")
print(f"\nConclusion: stock_value should use MRP={max(mrp_from_it, mrp_from_sc)}")
