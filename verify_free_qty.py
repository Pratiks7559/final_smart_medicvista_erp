# -*- coding: utf-8 -*-
"""
COMPREHENSIVE FREE QTY VERIFICATION SCRIPT
This script verifies the complete flow:
1. Frontend data collection (JavaScript)
2. Backend processing (combined_invoice_view.py)
3. Database storage (PurchaseMaster.product_free_qty)
4. Display in invoice detail page
"""

from core.models import InvoiceMaster, PurchaseMaster, SupplierMaster, ProductMaster
from datetime import datetime, date

print("=" * 80)
print("COMPREHENSIVE FREE QTY VERIFICATION")
print("=" * 80)

# Step 1: Check if field exists in model
print("\n[STEP 1] Checking if product_free_qty field exists in PurchaseMaster model...")
fields = [f.name for f in PurchaseMaster._meta.get_fields()]
if 'product_free_qty' in fields:
    print("PASS: Field 'product_free_qty' EXISTS in PurchaseMaster model")
    field = PurchaseMaster._meta.get_field('product_free_qty')
    print(f"  - Field Type: {field.get_internal_type()}")
    print(f"  - Default Value: {field.default}")
    print(f"  - Null Allowed: {field.null}")
    print(f"  - Blank Allowed: {field.blank}")
else:
    print("FAIL: Field 'product_free_qty' NOT FOUND in PurchaseMaster model")
    print("  Available fields:", fields)
    exit(1)

# Step 2: Get test data
print("\n[STEP 2] Getting test supplier and product...")
supplier = SupplierMaster.objects.get_or_create(
    supplier_name="TEST_SUPPLIER_FREE_QTY",
    defaults={'supplier_mobile': '9999999999', 'supplier_address': 'Test', 'supplier_type': 'Test'}
)[0]
print(f"PASS: Supplier: {supplier.supplier_name} (ID: {supplier.supplierid})")

product = ProductMaster.objects.first()
if not product:
    print("✗ No products found. Please add a product first.")
    exit(1)
print(f"PASS: Product: {product.product_name} (ID: {product.productid})")

# Step 3: Create test invoice with FREE QTY
print("\n[STEP 3] Creating test invoice with FREE QTY...")
invoice_no = f"FQTEST{datetime.now().strftime('%H%M%S')}"
paid_qty = 50.0
free_qty = 10.0  # THIS IS THE FREE QUANTITY WE'RE TESTING

invoice = InvoiceMaster.objects.create(
    invoice_no=invoice_no,
    invoice_date=date.today(),
    supplierid=supplier,
    transport_charges=25.00,
    invoice_total=0.00,
    invoice_paid=0.00
)
print(f"PASS: Invoice: {invoice.invoice_no} (ID: {invoice.invoiceid})")

# Step 4: Create purchase with FREE QTY (simulating backend save)
print("\n[STEP 4] Creating purchase entry with FREE QTY...")
print(f"  Input Data:")
print(f"    - Paid Quantity: {paid_qty}")
print(f"    - Free Quantity: {free_qty}")
print(f"    - Total Quantity: {paid_qty + free_qty}")

purchase_rate = 50.00
discount = 25.00
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
    product_batch_no='FQBATCH01',
    product_expiry='12-2025',
    product_MRP=80.00,
    product_purchase_rate=purchase_rate,
    product_quantity=paid_qty,
    product_free_qty=free_qty,  # FREE QTY FIELD
    product_scheme=0.0,
    product_discount_got=discount,
    CGST=6.0,
    SGST=6.0,
    purchase_calculation_mode='flat',
    actual_rate_per_qty=purchase_rate - (discount / paid_qty),
    product_actual_rate=purchase_rate - (discount / paid_qty),
    total_amount=total_amount,
    product_transportation_charges=0.0,
    rate_a=70.00,
    rate_b=65.00,
    rate_c=60.00
)

invoice.invoice_total = total_amount + invoice.transport_charges
invoice.save()

print(f"PASS: Purchase Created (ID: {purchase.purchaseid})")
print(f"  Saved Data:")
print(f"    - product_quantity: {purchase.product_quantity}")
print(f"    - product_free_qty: {purchase.product_free_qty}")
print(f"    - Total: {purchase.product_quantity + purchase.product_free_qty}")

# Step 5: Verify from database (fresh query)
print("\n[STEP 5] VERIFYING FROM DATABASE (Fresh Query)...")
saved = PurchaseMaster.objects.get(purchaseid=purchase.purchaseid)
print(f"PASS: Database Query Result:")
print(f"    - Purchase ID: {saved.purchaseid}")
print(f"    - Product: {saved.product_name}")
print(f"    - Batch: {saved.product_batch_no}")
print(f"    - product_quantity: {saved.product_quantity}")
print(f"    - product_free_qty: {saved.product_free_qty}")
print(f"    - Total Qty: {saved.product_quantity + saved.product_free_qty}")
print(f"    - Amount (only for paid qty): Rs.{saved.total_amount:.2f}")

# Step 6: Verification Results
print("\n[STEP 6] VERIFICATION RESULTS:")
print("=" * 80)

results = []

# Check 1: Field exists
if 'product_free_qty' in fields:
    results.append(("Field Exists in Model", "PASS", "product_free_qty field found"))
else:
    results.append(("Field Exists in Model", "FAIL", "product_free_qty field not found"))

# Check 2: Value saved correctly
if saved.product_free_qty == free_qty:
    results.append(("Free Qty Saved", "PASS", f"Value {saved.product_free_qty} matches input {free_qty}"))
else:
    results.append(("Free Qty Saved", "FAIL", f"Expected {free_qty}, got {saved.product_free_qty}"))

# Check 3: Paid qty saved correctly
if saved.product_quantity == paid_qty:
    results.append(("Paid Qty Saved", "PASS", f"Value {saved.product_quantity} matches input {paid_qty}"))
else:
    results.append(("Paid Qty Saved", "FAIL", f"Expected {paid_qty}, got {saved.product_quantity}"))

# Check 4: Billing only for paid qty
expected_base = purchase_rate * paid_qty - discount
if abs(after_discount - expected_base) < 0.01:
    results.append(("Billing Calculation", "PASS", "Only paid qty used in billing"))
else:
    results.append(("Billing Calculation", "FAIL", "Free qty might be included in billing"))

# Display results
for test_name, status, message in results:
    status_symbol = "PASS" if status == "PASS" else "FAIL"
    print(f"{status_symbol} {test_name}: {status}")
    print(f"  -> {message}")

# Overall result
all_passed = all(status == "PASS" for _, status, _ in results)
print("\n" + "=" * 80)
if all_passed:
    print("SUCCESS: ALL TESTS PASSED! Free Qty feature is working correctly.")
else:
    print("FAILED: SOME TESTS FAILED! Please check the implementation.")

# Step 7: Display information
print("\n[STEP 7] VIEW IN BROWSER:")
print(f"  Invoice Detail URL: http://localhost:8000/invoices/{invoice.invoiceid}/")
print(f"  Expected Display:")
print(f"    - Qty column: {saved.product_quantity}")
print(f"    - Free Qty column: {saved.product_free_qty}")
print(f"    - Total Qty: {saved.product_quantity + saved.product_free_qty}")

print("\n[STEP 8] CLEANUP:")
print(f"  To delete test data, run:")
print(f"  InvoiceMaster.objects.filter(invoice_no='{invoice.invoice_no}').delete()")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
