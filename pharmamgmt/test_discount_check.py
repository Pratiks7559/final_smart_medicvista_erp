"""
Discount Calculation & Storage Verification Script
Checks: Purchase, Sales, Challan (Supplier + Customer)
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from decimal import Decimal
from core.models import (
    InvoiceMaster, PurchaseMaster,
    SalesInvoiceMaster, SalesMaster,
    Challan1, SupplierChallanMaster,
    CustomerChallan, CustomerChallanMaster,
)
from django.db.models import Sum

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"
SEP  = "=" * 60
LINE = "-" * 60

def calc_product_wise_total(rate, qty, discount, calc_mode, cgst, sgst):
    sub = Decimal(str(rate)) * Decimal(str(qty))
    if calc_mode == 'percentage':
        disc_amt = (sub * Decimal(str(discount))) / Decimal('100')
    else:
        disc_amt = Decimal(str(discount))
    after = sub - disc_amt
    total = after + (after * Decimal(str(cgst)) / 100) + (after * Decimal(str(sgst)) / 100)
    return round(float(total), 2)

# ─────────────────────────────────────────────
# 1. PURCHASE INVOICES
# ─────────────────────────────────────────────
print("\n" + SEP)
print("1. PURCHASE INVOICES (InvoiceMaster + PurchaseMaster)")
print(SEP)

invoices = InvoiceMaster.objects.all().order_by('-invoiceid')[:20]
print("  Checking last %d invoices...\n" % invoices.count())

purchase_issues = 0
for inv in invoices:
    items = PurchaseMaster.objects.filter(product_invoiceid=inv)
    if not items.exists():
        continue

    items_total = 0.0
    line_errors = []
    for item in items:
        expected = calc_product_wise_total(
            item.product_purchase_rate,
            item.product_quantity,
            item.product_discount_got,
            item.purchase_calculation_mode,
            item.CGST,
            item.SGST
        )
        diff = abs(round(item.total_amount, 2) - expected)
        if diff > 0.05:
            line_errors.append(
                "    Product '%s' batch %s: stored=%.2f, expected=%.2f, diff=%.2f  [rate=%.2f qty=%.2f disc=%.2f mode=%s cgst=%.1f sgst=%.1f]"
                % (item.product_name, item.product_batch_no,
                   item.total_amount, expected, diff,
                   item.product_purchase_rate, item.product_quantity,
                   item.product_discount_got, item.purchase_calculation_mode,
                   item.CGST, item.SGST)
            )
        items_total += item.total_amount

    whole_disc = inv.whole_discount_amount if hasattr(inv, 'whole_discount_amount') else 0.0
    expected_inv_total = round(items_total + (inv.transport_charges or 0) - (whole_disc or 0))
    inv_diff = abs(round(inv.invoice_total) - expected_inv_total)
    has_whole_disc = (whole_disc or 0) > 0
    ok = (inv_diff <= 1) and not line_errors

    if not ok:
        purchase_issues += 1
        print("  %s  Invoice #%s (ID:%s)" % (FAIL, inv.invoice_no, inv.invoiceid))
        print("    invoice_total=%.2f  items_sum=%.2f  transport=%.2f  whole_disc=%.2f"
              % (inv.invoice_total, items_total, inv.transport_charges or 0, whole_disc or 0))
        print("    expected_total=%d  diff=%d" % (expected_inv_total, inv_diff))
        if line_errors:
            print("    --- Line item mismatches ---")
            for e in line_errors:
                print(e)
        else:
            print("    (line items OK — invoice_total itself was set differently, likely old data or manual edit)")
    else:
        disc_note = " [whole_disc=%.2f]" % whole_disc if has_whole_disc else ""
        print("  %s  Invoice #%s  total=%.2f%s" % (PASS, inv.invoice_no, inv.invoice_total, disc_note))

if purchase_issues == 0:
    print("\n  %s  All purchase invoices: totals match correctly." % PASS)
else:
    print("\n  %s  %d purchase invoice(s) have mismatches." % (FAIL, purchase_issues))

# ─────────────────────────────────────────────
# 2. SALES INVOICES
# ─────────────────────────────────────────────
print("\n" + SEP)
print("2. SALES INVOICES (SalesInvoiceMaster + SalesMaster)")
print(SEP)

sinvoices = SalesInvoiceMaster.objects.all().order_by('-sales_invoice_date')[:20]
print("  Checking last %d invoices...\n" % sinvoices.count())

sales_issues = 0
for inv in sinvoices:
    items = SalesMaster.objects.filter(sales_invoice_no=inv.sales_invoice_no)
    if not items.exists():
        continue

    items_total = 0.0
    line_errors = []
    for item in items:
        expected = calc_product_wise_total(
            item.sale_rate,
            item.sale_quantity,
            item.sale_discount,
            item.sale_calculation_mode or 'flat',
            item.sale_cgst,
            item.sale_sgst
        )
        diff = abs(round(item.sale_total_amount, 2) - expected)
        if diff > 0.05:
            line_errors.append(
                "    Product '%s' batch %s: stored=%.2f, expected=%.2f, diff=%.2f  [rate=%.2f qty=%.2f disc=%.2f mode=%s cgst=%.1f sgst=%.1f]"
                % (item.product_name, item.product_batch_no,
                   item.sale_total_amount, expected, diff,
                   item.sale_rate, item.sale_quantity,
                   item.sale_discount, item.sale_calculation_mode or 'flat',
                   item.sale_cgst, item.sale_sgst)
            )
        items_total += item.sale_total_amount

    computed_total = round(items_total + (inv.sales_transport_charges or 0) - (inv.whole_discount_amount or 0))
    property_total = inv.sales_invoice_total
    has_whole_disc = (inv.whole_discount_amount or 0) > 0
    ok = (abs(computed_total - property_total) <= 1) and not line_errors

    if not ok:
        sales_issues += 1
        print("  %s  Invoice #%s" % (FAIL, inv.sales_invoice_no))
        print("    property_total=%d  computed=%d  items_sum=%.2f  transport=%.2f  whole_disc=%.2f"
              % (property_total, computed_total, items_total,
                 inv.sales_transport_charges or 0, inv.whole_discount_amount or 0))
        for e in line_errors:
            print(e)
    else:
        disc_note = " [whole_disc=%.2f]" % inv.whole_discount_amount if has_whole_disc else ""
        print("  %s  Invoice #%s  total=%d%s" % (PASS, inv.sales_invoice_no, property_total, disc_note))

if sales_issues == 0:
    print("\n  %s  All sales invoices: totals match correctly." % PASS)
else:
    print("\n  %s  %d sales invoice(s) have mismatches." % (FAIL, sales_issues))

# ─────────────────────────────────────────────
# 3. SUPPLIER CHALLANS
# ─────────────────────────────────────────────
print("\n" + SEP)
print("3. SUPPLIER CHALLANS (Challan1 + SupplierChallanMaster)")
print(SEP)

challans = Challan1.objects.all().order_by('-challan_id')[:20]
print("  Checking last %d challans...\n" % challans.count())

sup_challan_issues = 0
for ch in challans:
    items = SupplierChallanMaster.objects.filter(product_challan_id=ch)
    if not items.exists():
        continue

    items_total = 0.0
    line_errors = []
    for item in items:
        expected = calc_product_wise_total(
            item.product_purchase_rate,
            item.product_quantity,
            item.product_discount,
            'flat',
            item.cgst,
            item.sgst
        )
        diff = abs(round(item.total_amount, 2) - expected)
        if diff > 0.05:
            line_errors.append(
                "    Product '%s' batch %s: stored=%.2f, expected=%.2f, diff=%.2f  [rate=%.2f qty=%.2f disc=%.2f cgst=%.1f sgst=%.1f]"
                % (item.product_name, item.product_batch_no,
                   item.total_amount, expected, diff,
                   item.product_purchase_rate, item.product_quantity,
                   item.product_discount, item.cgst, item.sgst)
            )
        items_total += item.total_amount

    expected_total = round(items_total + (ch.transport_charges or 0) - (ch.whole_discount_amount or 0), 2)
    diff = abs(round(ch.challan_total, 2) - round(expected_total, 2))
    has_whole_disc = (ch.whole_discount_amount or 0) > 0
    ok = (diff <= 0.05) and not line_errors

    if not ok:
        sup_challan_issues += 1
        print("  %s  Challan #%s (ID:%s)" % (FAIL, ch.challan_no, ch.challan_id))
        print("    challan_total=%.2f  items_sum=%.2f  transport=%.2f  whole_disc=%.2f"
              % (ch.challan_total, items_total, ch.transport_charges or 0, ch.whole_discount_amount or 0))
        print("    expected=%.2f  diff=%.2f" % (expected_total, diff))
        for e in line_errors:
            print(e)
    else:
        disc_note = " [whole_disc=%.2f]" % ch.whole_discount_amount if has_whole_disc else ""
        print("  %s  Challan #%s  total=%.2f%s" % (PASS, ch.challan_no, ch.challan_total, disc_note))

if sup_challan_issues == 0:
    print("\n  %s  All supplier challans: totals match correctly." % PASS)
else:
    print("\n  %s  %d supplier challan(s) have mismatches." % (FAIL, sup_challan_issues))

# ─────────────────────────────────────────────
# 4. CUSTOMER CHALLANS
# ─────────────────────────────────────────────
print("\n" + SEP)
print("4. CUSTOMER CHALLANS (CustomerChallan + CustomerChallanMaster)")
print(SEP)

cchallans = CustomerChallan.objects.all().order_by('-customer_challan_id')[:20]
print("  Checking last %d challans...\n" % cchallans.count())

cust_challan_issues = 0
for ch in cchallans:
    items = CustomerChallanMaster.objects.filter(customer_challan_id=ch)
    if not items.exists():
        continue

    items_total = 0.0
    line_errors = []
    for item in items:
        expected = calc_product_wise_total(
            item.sale_rate,
            item.sale_quantity,
            item.sale_discount,
            'flat',
            item.sale_cgst,
            item.sale_sgst
        )
        diff = abs(round(item.sale_total_amount, 2) - expected)
        if diff > 0.05:
            line_errors.append(
                "    Product '%s' batch %s: stored=%.2f, expected=%.2f, diff=%.2f  [rate=%.2f qty=%.2f disc=%.2f cgst=%.1f sgst=%.1f]"
                % (item.product_name, item.product_batch_no,
                   item.sale_total_amount, expected, diff,
                   item.sale_rate, item.sale_quantity,
                   item.sale_discount, item.sale_cgst, item.sale_sgst)
            )
        items_total += item.sale_total_amount

    expected_total = round(items_total + (ch.customer_transport_charges or 0) - (ch.whole_discount_amount or 0), 2)
    diff = abs(round(ch.challan_total, 2) - round(expected_total, 2))
    has_whole_disc = (ch.whole_discount_amount or 0) > 0
    ok = (diff <= 0.05) and not line_errors

    if not ok:
        cust_challan_issues += 1
        print("  %s  Challan #%s (ID:%s)" % (FAIL, ch.customer_challan_no, ch.customer_challan_id))
        print("    challan_total=%.2f  items_sum=%.2f  transport=%.2f  whole_disc=%.2f"
              % (ch.challan_total, items_total, ch.customer_transport_charges or 0, ch.whole_discount_amount or 0))
        print("    expected=%.2f  diff=%.2f" % (expected_total, diff))
        for e in line_errors:
            print(e)
    else:
        disc_note = " [whole_disc=%.2f]" % ch.whole_discount_amount if has_whole_disc else ""
        print("  %s  Challan #%s  total=%.2f%s" % (PASS, ch.customer_challan_no, ch.challan_total, disc_note))

if cust_challan_issues == 0:
    print("\n  %s  All customer challans: totals match correctly." % PASS)
else:
    print("\n  %s  %d customer challan(s) have mismatches." % (FAIL, cust_challan_issues))

# ─────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────
print("\n" + SEP)
print("SUMMARY")
print(SEP)
total_issues = purchase_issues + sales_issues + sup_challan_issues + cust_challan_issues
print("  Purchase Invoice issues : %d" % purchase_issues)
print("  Sales Invoice issues    : %d" % sales_issues)
print("  Supplier Challan issues : %d" % sup_challan_issues)
print("  Customer Challan issues : %d" % cust_challan_issues)
print("  " + LINE)
print("  Total issues            : %d" % total_issues)
if total_issues == 0:
    print("\n  %s  Everything is calculating and storing correctly!" % PASS)
else:
    print("\n  %s  %d issue(s) found -- see details above." % (FAIL, total_issues))
    if purchase_issues > 0:
        print("\n  NOTE: Purchase invoice mismatches are likely OLD data entered manually")
        print("  before the combined invoice form was built. New invoices via the form")
        print("  should be correct. Check if the failing invoices are test/old entries.")
print()
