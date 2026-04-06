import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SupplierChallanMaster, Challan1
from core.fast_inventory import FastInventory

sc = SupplierChallanMaster.objects.filter(product_id=2).first()
if sc:
    print('batch:', sc.product_batch_no)
    print('qty:', sc.product_quantity)
    print('challan_id:', sc.product_challan_id_id)
    challan = Challan1.objects.get(challan_id=sc.product_challan_id_id)
    print('is_invoiced:', challan.is_invoiced)

print()
print('FastInventory result (no FY filter):')
inv = FastInventory.get_batch_inventory_data('')
for item in inv:
    if '1ST AID' in item.get('product_name',''):
        print(' ', item)

print()
print('All batches in FastInventory:')
for item in inv:
    print(f"  {item['product_name']} | batch={item['batch_no']} | stock={item['stock']}")
