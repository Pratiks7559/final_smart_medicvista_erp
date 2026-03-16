from core.models import InvoiceMaster, PurchaseMaster, SupplierMaster, ProductMaster
from datetime import datetime, date
from django.db import transaction

print("=" * 80)
print("TESTING FREE QTY FUNCTIONALITY")
print("=" * 80)

# Get or create test supplier
supplier, _ = SupplierMaster.objects.get_or_create(
    supplier_name="TEST_SUPPLIER_FREE_QTY",
    defaults={'supplier_mobile': '9999999999', 'supplier_address': 'Test', 'supplier_type': 'Test'}
)
print(f"\n1. Supplier: {supplier.supplier_name} (ID: {supplier.supplierid})")

# Get or create test product
product, _ = ProductMaster.objects.get_or_create(
    product_name="TEST_PRODUCT_FREE_QTY",
    defaults={'product_company': 'Test', 'product_packing': '10x10', 'product_MRP': 100.00, 'product_HSN': '12345678'}
)
print(f"2. Product: {product.product_name} (ID: {product.productid})")

# Create invoice
invoice_no = f"TEST_FQ_{datetime.now().strftime('%Y%m%d%H%M%S')}"
invoice = InvoiceMaster.objects.create(
    invoice_no=invoice_no,
    invoice_date=date.today(),
    supplierid=supplier,
    transport_charges=50.00,
    invoice_total=0.00,
    invoice_paid=0.00
)
print(f"3. Invoice: {invoice.invoice_no} (ID: {invoice.invoiceid})")

# Create purchase with FREE QTY
paid_qty = 100.0
free_qty = 25.0
purchase_rate = 80.00
discount = 50.00
cgst = 6.0
sgst = 6.0

base_amount = purchase_rate * paid_qty
after_discount = base_amount - discount
cgst_amount = (after_discount * cgst) / 100
sgst_amount = (after_discount * sgst) / 100
total_amount = after_discount + cgst_amount + sgst_amount

purchase = PurchaseMaster.objects.create(
    product_supplierid=supplier,
    product_invoiceid=invoice,
    product_invoice_no=invoice.invoice_no,
    productid=product,
    product_name=product.product_name,
    product_company=product.product_company,
    product_packing=product.product_packing,
    product_batch_no='BATCH_TEST_001',
    product_expiry='12-2025',
    product_MRP=100.00,
    product_purchase_rate=purchase_rate,
    product_quantity=paid_qty,
    product_free_qty=free_qty,
    product_scheme=0.0,
    product_discount_got=discount,
    CGST=cgst,
    SGST=sgst,
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

print(f"4. Purchase Created (ID: {purchase.purchaseid})")
print(f"   - Paid Qty: {purchase.product_quantity}")
print(f"   - Free Qty: {purchase.product_free_qty}")
print(f"   - Total: {purchase.product_quantity + purchase.product_free_qty}")

# Verify from database
saved = PurchaseMaster.objects.get(purchaseid=purchase.purchaseid)
print(f"\n5. DATABASE VERIFICATION:")
print(f"   - Purchase ID: {saved.purchaseid}")
print(f"   - Paid Qty: {saved.product_quantity}")
print(f"   - Free Qty: {saved.product_free_qty}")

if saved.product_free_qty == free_qty:
    print(f"\n✅ SUCCESS! Free Qty is saved correctly: {saved.product_free_qty}")
else:
    print(f"\n❌ FAILED! Free Qty mismatch - Expected: {free_qty}, Found: {saved.product_free_qty}")

print(f"\n6. VIEW IN BROWSER:")
print(f"   URL: http://localhost:8000/invoices/{invoice.invoiceid}/")

print(f"\n7. DELETE TEST DATA:")
print(f"   InvoiceMaster.objects.filter(invoice_no='{invoice.invoice_no}').delete()")

print("\n" + "=" * 80)
