import os
import sys
import django

# Setup Django
sys.path.append(r'c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster, SalesInvoiceMaster

print("=" * 80)
print("CHECKING SALES DATA FOR FREE QTY FIELD")
print("=" * 80)

# Get total sales count
total_sales = SalesMaster.objects.count()
print(f"\nTotal Sales Records: {total_sales}")

if total_sales == 0:
    print("\n❌ NO SALES DATA FOUND IN DATABASE!")
    print("   Please create some sales invoices first.")
else:
    # Check if sale_free_qty field has any non-zero values
    sales_with_free_qty = SalesMaster.objects.filter(sale_free_qty__gt=0).count()
    print(f"Sales with Free Qty > 0: {sales_with_free_qty}")
    
    # Get latest 5 sales
    print("\n" + "=" * 80)
    print("LATEST 5 SALES RECORDS:")
    print("=" * 80)
    
    latest_sales = SalesMaster.objects.select_related('sales_invoice_no', 'productid').order_by('-id')[:5]
    
    for sale in latest_sales:
        print(f"\nSale ID: {sale.id}")
        print(f"Invoice: {sale.sales_invoice_no.sales_invoice_no}")
        print(f"Product: {sale.product_name}")
        print(f"Batch: {sale.product_batch_no}")
        print(f"Quantity: {sale.sale_quantity}")
        print(f"Free Qty: {sale.sale_free_qty} ← THIS IS THE FIELD")
        print(f"Total: ₹{sale.sale_total_amount}")
        print("-" * 80)
    
    # Check if any invoice has products
    print("\n" + "=" * 80)
    print("CHECKING INVOICE WITH PRODUCTS:")
    print("=" * 80)
    
    invoice_with_sales = SalesInvoiceMaster.objects.filter(
        salesmaster__isnull=False
    ).distinct().first()
    
    if invoice_with_sales:
        print(f"\nInvoice No: {invoice_with_sales.sales_invoice_no}")
        print(f"Customer: {invoice_with_sales.customerid.customer_name}")
        print(f"Date: {invoice_with_sales.sales_invoice_date}")
        
        sales_items = SalesMaster.objects.filter(sales_invoice_no=invoice_with_sales.sales_invoice_no)
        print(f"\nTotal Products: {sales_items.count()}")
        
        print("\nProduct Details:")
        for idx, sale in enumerate(sales_items, 1):
            print(f"{idx}. {sale.product_name} | Qty: {sale.sale_quantity} | Free Qty: {sale.sale_free_qty}")
    else:
        print("\n❌ No invoices with sales items found!")

print("\n" + "=" * 80)
print("FIELD VERIFICATION:")
print("=" * 80)

# Verify field exists in model
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("PRAGMA table_info(core_salesmaster)")
    columns = cursor.fetchall()
    
    print("\nAll columns in SalesMaster table:")
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        if 'free' in col_name.lower():
            print(f"  ✓ {col_name} ({col_type}) ← FREE QTY FIELD FOUND!")
        else:
            print(f"    {col_name} ({col_type})")

print("\n" + "=" * 80)
