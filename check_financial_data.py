import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster, PurchaseMaster, CustomerChallanMaster, SupplierChallanMaster

print("=" * 70)
print("DATABASE DATA CHECK FOR FINANCIAL REPORT")
print("=" * 70)

# Check Sales
print("\n1. SALES DATA:")
sales_count = SalesMaster.objects.count()
print(f"   Total Sales Records: {sales_count}")

if sales_count > 0:
    print("\n   Recent Sales:")
    for sale in SalesMaster.objects.select_related('sales_invoice_no', 'customerid')[:5]:
        print(f"   - Invoice: {sale.sales_invoice_no.sales_invoice_no}")
        print(f"     Date: {sale.sale_entry_date.strftime('%d-%m-%Y')}")
        print(f"     Customer: {sale.customerid.customer_name}")
        print(f"     Product: {sale.product_name}")
        print(f"     Qty: {sale.sale_quantity}, Rate: {sale.sale_rate}")
        print()
else:
    print("   WARNING: NO SALES DATA FOUND!")

# Check Purchases
print("\n2. PURCHASE DATA:")
purchase_count = PurchaseMaster.objects.count()
print(f"   Total Purchase Records: {purchase_count}")

if purchase_count > 0:
    print("\n   Recent Purchases:")
    for purchase in PurchaseMaster.objects.select_related('product_supplierid')[:5]:
        print(f"   - Invoice: {purchase.product_invoice_no}")
        print(f"     Date: {purchase.purchase_entry_date.strftime('%d-%m-%Y')}")
        print(f"     Supplier: {purchase.product_supplierid.supplier_name}")
        print(f"     Product: {purchase.product_name}")
        print(f"     Qty: {purchase.product_quantity}, Rate: {purchase.product_purchase_rate}")
        print()
else:
    print("   WARNING: NO PURCHASE DATA FOUND!")

# Check Customer Challans
print("\n3. CUSTOMER CHALLAN DATA:")
customer_challan_count = CustomerChallanMaster.objects.count()
print(f"   Total Customer Challan Records: {customer_challan_count}")

if customer_challan_count > 0:
    print("\n   Recent Customer Challans:")
    for challan in CustomerChallanMaster.objects.select_related('customer_name')[:3]:
        print(f"   - Challan: {challan.customer_challan_no}")
        print(f"     Date: {challan.sales_entry_date.strftime('%d-%m-%Y')}")
        print(f"     Customer: {challan.customer_name.customer_name}")
        print(f"     Product: {challan.product_name}")
        print()

# Check Supplier Challans
print("\n4. SUPPLIER CHALLAN DATA:")
supplier_challan_count = SupplierChallanMaster.objects.count()
print(f"   Total Supplier Challan Records: {supplier_challan_count}")

if supplier_challan_count > 0:
    print("\n   Recent Supplier Challans:")
    for challan in SupplierChallanMaster.objects.select_related('product_suppliername')[:3]:
        print(f"   - Challan: {challan.product_challan_no}")
        print(f"     Date: {challan.challan_entry_date.strftime('%d-%m-%Y')}")
        print(f"     Supplier: {challan.product_suppliername.supplier_name}")
        print(f"     Product: {challan.product_name}")
        print()

# Summary
print("\n" + "=" * 70)
print("SUMMARY:")
print("=" * 70)
total_records = sales_count + purchase_count + customer_challan_count + supplier_challan_count
print(f"Total Records Available for Financial Report: {total_records}")
print(f"  - Sales: {sales_count}")
print(f"  - Purchases: {purchase_count}")
print(f"  - Customer Challans: {customer_challan_count}")
print(f"  - Supplier Challans: {supplier_challan_count}")

if total_records == 0:
    print("\nNO DATA AVAILABLE!")
    print("   Financial report exports will only show column headers.")
    print("   Please add some sales or purchase data first.")
elif sales_count == 0:
    print("\nWARNING: No sales data found!")
    print("   Financial report will only show purchase transactions.")
else:
    print("\nData is available for financial report export.")

print("=" * 70)
