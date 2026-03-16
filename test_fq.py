# -*- coding: utf-8 -*-
from core.models import InvoiceMaster, PurchaseMaster, SupplierMaster, ProductMaster
from datetime import datetime, date

print("Testing FREE QTY Functionality")
print("=" * 60)

# Get or create test supplier
supplier, _ = SupplierMaster.objects.get_or_create(
    supplier_name="TEST_SUPPLIER_FREE_QTY",
    defaults={'supplier_mobile': '9999999999', 'supplier_address': 'Test', 'supplier_type': 'Test'}
)
print(f"Supplier: {supplier.supplier_name}")

# Get existing product from database
product = ProductMaster.objects.first()
if not product:
    print("ERROR: No products found in database. Please add a product first.")
    exit()
print(f"Product: {product.product_name}")

# Create invoice
invoice_no = f"TFQT{datetime.now().strftime('%H%M%S')}"
invoice = InvoiceMaster.objects.create(
    invoice_no=invoice_no,
    invoice_date=date.today(),
    supplierid=supplier,
    transport_charges=50.00,
    invoice_total=0.00,
    invoice_paid=0.00
)
print(f"Invoice: {invoice.invoice_no}")

# Create purchase with FREE QTY
paid_qty = 100.0
free_qty = 25.0
purchase_rate = 80.00
discount = 50.00

base_amount = purchase_rate * paid_qty
after_discount = base_amount - discount
cgst_amount = (after_discount * 6.0) / 100
sgst_amount = (after_discount * 6.0) / 100
total_amount = after_discount + cgst_amount + sgst_amount

purchase = PurchaseMaster.objects.create(
    product_supplierid=supplier,
    product_invoiceid=invoice,
    product_invoice_no=invoice.invoice_no,
    productid=product,
    product_name=product.product_name,
    product_company=product.product_company,
    product_packing=product.product_packing,
    product_batch_no='BATCH001',
    product_expiry='12-2025',
    product_MRP=100.00,
    product_purchase_rate=purchase_rate,
    product_quantity=paid_qty,
    product_free_qty=free_qty,
    product_scheme=0.0,
    product_discount_got=discount,
    CGST=6.0,
    SGST=6.0,
    purchase_calculation_mode='flat',
    actual_rate_per_qty=purchase_rate - (discount / paid_qty),
    product_actual_rate=purchase_rate - (discount / paid_qty),
    total_amount=total_amount,
    product_transportation_charges=0.0,
    rate_a=90.00,
    rate_b=85.00,
    rate_c=82.00
)

invoice.invoice_total = total_amount + invoice.transport_charges
invoice.save()

print(f"Purchase ID: {purchase.purchaseid}")
print(f"Paid Qty: {purchase.product_quantity}")
print(f"Free Qty: {purchase.product_free_qty}")

# Verify from database
saved = PurchaseMaster.objects.get(purchaseid=purchase.purchaseid)
print(f"\nDATABASE CHECK:")
print(f"Paid Qty: {saved.product_quantity}")
print(f"Free Qty: {saved.product_free_qty}")

if saved.product_free_qty == free_qty:
    print(f"\nSUCCESS! Free Qty saved: {saved.product_free_qty}")
else:
    print(f"\nFAILED! Expected: {free_qty}, Found: {saved.product_free_qty}")

print(f"\nView at: http://localhost:8000/invoices/{invoice.invoiceid}/")
print(f"Delete: InvoiceMaster.objects.filter(invoice_no='{invoice.invoice_no}').delete()")
