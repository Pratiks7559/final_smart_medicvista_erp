import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import SalesMaster, PurchaseMaster, SupplierChallanMaster, CustomerChallanMaster

print("=== SIMULATING PDF GENERATION ===\n")

# Get data
sales_query = SalesMaster.objects.select_related('productid', 'sales_invoice_no', 'customerid')
purchase_query = PurchaseMaster.objects.select_related('productid', 'product_invoiceid', 'product_supplierid')
supplier_challan_query = SupplierChallanMaster.objects.select_related('product_id', 'product_suppliername', 'product_challan_id')
customer_challan_query = CustomerChallanMaster.objects.select_related('product_id', 'customer_name', 'customer_challan_id')

print(f"Sales Query Count: {sales_query.count()}")
print(f"Purchase Query Count: {purchase_query.count()}")
print(f"Customer Challan Query Count: {customer_challan_query.count()}")
print(f"Supplier Challan Query Count: {supplier_challan_query.count()}")

all_txns = []

# Process Purchases
print("\n=== PROCESSING PURCHASES ===")
for purchase in purchase_query:
    try:
        quantity = float(purchase.product_quantity)
        purchase_rate = float(purchase.product_purchase_rate)
        purchase_cost = purchase_rate * quantity
        gst_amount = purchase_cost * (float(purchase.CGST) + float(purchase.SGST)) / 100
        profit = -purchase_cost
        
        txn = {
            'date': purchase.purchase_entry_date,
            'type': 'Purchase',
            'invoice': purchase.product_invoice_no,
            'party': purchase.product_supplierid.supplier_name,
            'product': purchase.product_name[:15],
            'batch': purchase.product_batch_no,
            'qty': quantity,
            'p_rate': purchase_rate,
            's_rate': 0,
            'gst': gst_amount,
            'profit': profit,
            'sales': 0
        }
        all_txns.append(txn)
        print(f"Added: {txn['date']} | {txn['type']} | {txn['invoice']} | {txn['party']} | Qty: {txn['qty']}")
    except Exception as e:
        print(f"Error processing purchase: {e}")

print(f"\nTotal Transactions: {len(all_txns)}")

if all_txns:
    print("\n=== SAMPLE TRANSACTION ===")
    print(all_txns[0])
else:
    print("\n!!! NO TRANSACTIONS FOUND !!!")
