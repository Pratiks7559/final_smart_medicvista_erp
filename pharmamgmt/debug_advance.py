import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'pharmamgmt.settings'
django.setup()

from core.models import SupplierAdvance, AdvanceLedger, SupplierMaster, InvoiceMaster, InvoicePaid

s = SupplierMaster.objects.first()
print('Supplier:', s.supplier_name, '| ID:', s.supplierid)

print('\n--- SupplierAdvance rows ---')
for a in SupplierAdvance.objects.filter(supplier=s):
    print(f'  ID:{a.advance_id}  amount:{a.amount}  date:{a.payment_date}  mode:{a.payment_mode}')

print('\n--- AdvanceLedger rows ---')
for e in AdvanceLedger.objects.filter(supplier=s):
    print(f'  {e.entry_type}  amount:{e.amount}  ref:{e.invoice_ref}  narration:{e.narration}')

print('\n--- Last 5 Invoices ---')
for inv in InvoiceMaster.objects.filter(supplierid=s).order_by('-invoiceid')[:5]:
    print(f'  inv:{inv.invoice_no}  total:{inv.invoice_total}  paid:{inv.invoice_paid}  status:{inv.payment_status}')

print('\n--- Last 5 InvoicePaid ---')
for p in InvoicePaid.objects.filter(ip_invoiceid__supplierid=s).order_by('-payment_id')[:5]:
    print(f'  inv:{p.ip_invoiceid.invoice_no}  amount:{p.payment_amount}  mode:{p.payment_mode}  ref:{p.payment_ref_no}')

