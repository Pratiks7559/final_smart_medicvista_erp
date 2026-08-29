import os, django, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'pharmamgmt.settings'
django.setup()

from core.models import SupplierAdvance, AdvanceLedger, SupplierMaster, InvoiceMaster, InvoicePaid
from core.unified_payment_view import _apply_supplier_advance_to_invoices
from datetime import date

s = SupplierMaster.objects.first()
print('Supplier:', s.supplier_name)

# Check advance
adv = SupplierAdvance.objects.filter(supplier=s, amount__gt=0)
print('Advances before:', [(a.advance_id, a.amount) for a in adv])

# Check latest invoice
inv = InvoiceMaster.objects.filter(supplierid=s).order_by('-invoiceid').first()
if inv:
    print('Latest invoice:', inv.invoice_no, 'total:', inv.invoice_total, 'paid:', inv.invoice_paid, 'status:', inv.payment_status)

# Manually trigger adjust
print('\nRunning _apply_supplier_advance_to_invoices...')
try:
    adjusted = _apply_supplier_advance_to_invoices(s, date.today())
    print('Adjusted amount:', adjusted)
except Exception as e:
    import traceback
    traceback.print_exc()

# Check after
print('\nAdvances after:', [(a.advance_id, a.amount) for a in SupplierAdvance.objects.filter(supplier=s)])
print('Ledger entries:', [(e.entry_type, e.amount, e.invoice_ref) for e in AdvanceLedger.objects.filter(supplier=s)])
inv2 = InvoiceMaster.objects.filter(supplierid=s).order_by('-invoiceid').first()
if inv2:
    print('Invoice after:', inv2.invoice_no, 'paid:', inv2.invoice_paid, 'status:', inv2.payment_status)
print('InvoicePaid entries:', [(p.payment_amount, p.payment_ref_no) for p in InvoicePaid.objects.filter(ip_invoiceid__supplierid=s).order_by('-payment_id')[:3]])
