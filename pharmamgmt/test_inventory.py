import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import InventoryTransaction, PurchaseMaster, InvoiceMaster, ProductMaster
from core.year_filter_utils import get_current_financial_year, get_financial_year_dates
from django.db.models import Sum

print("=" * 60)
print("FY INVOICE DATE FILTER TEST")
print("=" * 60)

# Test all 3 invoices
all_invoices = InvoiceMaster.objects.all()
print(f"\nAll Invoices:")
for inv in all_invoices:
    print(f"  id={inv.invoiceid} | date={inv.invoice_date}")

# Test each FY
test_years = [2011, 2012, 2013, 2025, 2026]
for year in test_years:
    fy_start, fy_end = get_financial_year_dates(year)
    inv_ids = list(InvoiceMaster.objects.filter(
        invoice_date__gte=fy_start,
        invoice_date__lte=fy_end
    ).values_list('invoiceid', flat=True))

    prod_ids = list(PurchaseMaster.objects.filter(
        product_invoiceid__in=inv_ids
    ).values_list('productid_id', flat=True).distinct())

    it_count = InventoryTransaction.objects.filter(
        product_id__in=prod_ids
    ).count()

    print(f"\nFY {year}-{str(year+1)[2:]} ({fy_start} to {fy_end}):")
    print(f"  Invoice IDs in FY : {inv_ids}")
    print(f"  Product IDs in FY : {prod_ids}")
    print(f"  IT rows for these : {it_count}")
    if prod_ids:
        for pid in prod_ids:
            try:
                p = ProductMaster.objects.get(productid=pid)
                stock = InventoryTransaction.objects.filter(product_id=pid).aggregate(s=Sum('quantity'))['s'] or 0
                print(f"    -> {p.product_name} | stock={stock}")
            except:
                pass

print("\n" + "=" * 60)
print("CURRENT FY TEST")
print("=" * 60)
current_fy = get_current_financial_year()
fy_start, fy_end = get_financial_year_dates(current_fy)
print(f"Current FY: {current_fy}-{str(current_fy+1)[2:]} ({fy_start} to {fy_end})")

inv_ids = list(InvoiceMaster.objects.filter(
    invoice_date__gte=fy_start, invoice_date__lte=fy_end
).values_list('invoiceid', flat=True))
prod_ids = list(PurchaseMaster.objects.filter(
    product_invoiceid__in=inv_ids
).values_list('productid_id', flat=True).distinct())
it_rows = InventoryTransaction.objects.filter(product_id__in=prod_ids).count()

print(f"Products in current FY: {len(prod_ids)}")
print(f"IT rows shown         : {it_rows}")
if it_rows == 0:
    print("\nWARNING: Current FY me koi purchase invoice nahi hai!")
    print("=> Inventory page blank dikhega")
    print("=> Navbar se sahi FY select karo jisme purchases hain")
else:
    print("\nOK: Data dikh raha hai!")
