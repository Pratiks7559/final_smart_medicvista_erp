from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from datetime import datetime
from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_GET
from .models import (
    InvoiceMaster, InvoicePaid, SalesInvoiceMaster, SalesInvoicePaid,
    SupplierMaster, CustomerMaster, SupplierAdvance, CustomerAdvance, AdvanceLedger
)


@login_required
def add_unified_payment(request):
    if request.method == 'POST':
        try:
            transaction_type = request.POST.get('transaction_type')
            payment_date_str = request.POST.get('payment_date')
            payment_amount   = request.POST.get('payment_amount')
            payment_mode     = request.POST.get('payment_mode')
            reference_no     = request.POST.get('reference_no', '')
            entity_id        = request.POST.get('entity_id')

            if not all([transaction_type, payment_date_str, payment_amount, payment_mode]):
                messages.error(request, 'Please fill all required fields.')
                return redirect('add_unified_payment')

            if transaction_type not in ['payment', 'receipt']:
                messages.error(request, 'Invalid transaction type.')
                return redirect('add_unified_payment')

            if not entity_id:
                messages.error(request, 'Please select a supplier/customer first.')
                return redirect('add_unified_payment')

            try:
                amount = Decimal(str(payment_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if amount <= 0:
                    messages.error(request, 'Amount must be greater than 0.')
                    return redirect('add_unified_payment')
            except (ValueError, TypeError):
                messages.error(request, 'Invalid amount.')
                return redirect('add_unified_payment')

            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid date format.')
                return redirect('add_unified_payment')

            bank_name = request.POST.get('bank_name', '').strip()
            if payment_mode == 'bank':
                if not bank_name:
                    messages.error(request, 'Bank name is required for bank transfer.')
                    return redirect('add_unified_payment')
                payment_mode = f'bank - {bank_name}'

            with transaction.atomic():
                if transaction_type == 'payment':
                    try:
                        supplier = SupplierMaster.objects.get(supplierid=entity_id)
                    except SupplierMaster.DoesNotExist:
                        messages.error(request, 'Supplier not found.')
                        return redirect('add_unified_payment')

                    pending_invoices = list(InvoiceMaster.objects.filter(
                        supplierid=supplier
                    ).order_by('invoice_date'))

                    remaining = amount
                    updated = []
                    advance_used = Decimal('0')

                    # Get existing advance balance
                    advance_qs = list(SupplierAdvance.objects.filter(supplier=supplier, amount__gt=0).order_by('payment_date'))

                    for inv in pending_invoices:
                        inv_total   = Decimal(str(inv.invoice_total or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        inv_paid    = Decimal(str(inv.invoice_paid or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        inv_balance = inv_total - inv_paid
                        if inv_balance <= 0:
                            continue

                        inv_updated = False

                        # Step 1: Use existing advance first
                        for adv in advance_qs:
                            if adv.amount <= 0 or inv_balance <= 0:
                                continue
                            adv_amount = Decimal(str(adv.amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            apply_adv = min(adv_amount, inv_balance)
                            InvoicePaid.objects.create(
                                ip_invoiceid=inv,
                                payment_date=payment_date,
                                payment_amount=float(apply_adv),
                                payment_mode=adv.payment_mode,
                                payment_ref_no=f'ADV-ADJ-{adv.advance_id}'
                            )
                            AdvanceLedger.objects.create(
                                party_type='supplier',
                                supplier=supplier,
                                entry_type='adjusted',
                                amount=float(apply_adv),
                                entry_date=payment_date,
                                invoice_ref=inv.invoice_no,
                                narration=f'Advance adjusted against Invoice {inv.invoice_no}'
                            )
                            inv_balance -= apply_adv
                            inv_paid += apply_adv
                            adv.amount = float(adv_amount - apply_adv)
                            adv.save()
                            advance_used += apply_adv
                            inv_updated = True

                        # Step 2: Apply new payment amount to remaining balance
                        if inv_balance > 0 and remaining > 0:
                            apply = min(remaining, inv_balance)
                            InvoicePaid.objects.create(
                                ip_invoiceid=inv,
                                payment_date=payment_date,
                                payment_amount=float(apply),
                                payment_mode=payment_mode,
                                payment_ref_no=reference_no
                            )
                            inv_paid += apply
                            inv_balance -= apply
                            remaining -= apply
                            inv_updated = True

                        if inv_updated:
                            new_paid = float(inv_paid)
                            new_balance = float(inv_total) - new_paid
                            if round(new_balance) <= 0:
                                inv.payment_status = 'paid'
                            elif new_paid > 0:
                                inv.payment_status = 'partial'
                            inv.invoice_paid = new_paid
                            inv.save()
                            updated.append(inv.invoice_no)

                    # Remaining new payment -> save as advance
                    if remaining > 0:
                        SupplierAdvance.objects.create(
                            supplier=supplier,
                            amount=float(remaining),
                            payment_date=payment_date,
                            payment_mode=payment_mode,
                            reference_no=reference_no,
                            narration=f'Advance from over-payment of Rs.{amount}'
                        )
                        AdvanceLedger.objects.create(
                            party_type='supplier',
                            supplier=supplier,
                            entry_type='advance_in',
                            amount=float(remaining),
                            entry_date=payment_date,
                            narration=f'Advance received Rs.{remaining} (over-payment)'
                        )
                        if updated:
                            messages.success(request, f'Payment applied to {len(updated)} invoice(s). Rs.{remaining} saved as advance.')
                        else:
                            messages.success(request, f'Rs.{amount} saved as advance (no pending invoices).')
                    elif updated:
                        adv_msg = f' (Rs.{advance_used} from existing advance)' if advance_used > 0 else ''
                        messages.success(request, f'Payment applied to {len(updated)} invoice(s): {", ".join(updated)}.{adv_msg}')
                    elif advance_used > 0:
                        messages.success(request, f'Rs.{advance_used} advance adjusted against invoices.')
                    else:
                        messages.warning(request, 'No pending invoices found for this supplier.')

                elif transaction_type == 'receipt':
                    try:
                        customer = CustomerMaster.objects.get(customerid=entity_id)
                    except CustomerMaster.DoesNotExist:
                        messages.error(request, 'Customer not found.')
                        return redirect('add_unified_payment')

                    pending_invoices = list(SalesInvoiceMaster.objects.filter(
                        customerid=customer
                    ).order_by('sales_invoice_date'))

                    remaining = amount
                    updated = []
                    advance_used = Decimal('0')

                    advance_qs = list(CustomerAdvance.objects.filter(customer=customer, amount__gt=0).order_by('receipt_date'))

                    for inv in pending_invoices:
                        inv_total   = Decimal(str(inv.sales_invoice_total or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        inv_paid    = Decimal(str(inv.sales_invoice_paid or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        inv_balance = inv_total - inv_paid
                        if inv_balance <= 0:
                            continue

                        inv_updated = False

                        # Step 1: Use existing advance first
                        for adv in advance_qs:
                            if adv.amount <= 0 or inv_balance <= 0:
                                continue
                            adv_amount = Decimal(str(adv.amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                            apply_adv = min(adv_amount, inv_balance)
                            SalesInvoicePaid.objects.create(
                                sales_ip_invoice_no=inv,
                                sales_payment_date=payment_date,
                                sales_payment_amount=float(apply_adv),
                                sales_payment_mode=adv.receipt_mode,
                                sales_payment_ref_no=f'ADV-ADJ-{adv.advance_id}'
                            )
                            AdvanceLedger.objects.create(
                                party_type='customer',
                                customer=customer,
                                entry_type='adjusted',
                                amount=float(apply_adv),
                                entry_date=payment_date,
                                invoice_ref=inv.sales_invoice_no,
                                narration=f'Advance adjusted against Invoice {inv.sales_invoice_no}'
                            )
                            inv_balance -= apply_adv
                            inv_paid += apply_adv
                            adv.amount = float(adv_amount - apply_adv)
                            adv.save()
                            advance_used += apply_adv
                            inv_updated = True

                        # Step 2: Apply new receipt amount to remaining balance
                        if inv_balance > 0 and remaining > 0:
                            apply = min(remaining, inv_balance)
                            SalesInvoicePaid.objects.create(
                                sales_ip_invoice_no=inv,
                                sales_payment_date=payment_date,
                                sales_payment_amount=float(apply),
                                sales_payment_mode=payment_mode,
                                sales_payment_ref_no=reference_no
                            )
                            inv_paid += apply
                            inv_balance -= apply
                            remaining -= apply
                            inv_updated = True

                        if inv_updated:
                            new_paid = float(inv_paid)
                            new_balance = float(inv_total) - new_paid
                            if round(new_balance) <= 0:
                                inv.payment_status = 'paid'
                            elif new_paid > 0:
                                inv.payment_status = 'partial'
                            inv.sales_invoice_paid = new_paid
                            inv.save()
                            updated.append(inv.sales_invoice_no)

                    # Remaining new receipt -> save as advance
                    if remaining > 0:
                        CustomerAdvance.objects.create(
                            customer=customer,
                            amount=float(remaining),
                            receipt_date=payment_date,
                            receipt_mode=payment_mode,
                            reference_no=reference_no,
                            narration=f'Advance from over-receipt of Rs.{amount}'
                        )
                        AdvanceLedger.objects.create(
                            party_type='customer',
                            customer=customer,
                            entry_type='advance_in',
                            amount=float(remaining),
                            entry_date=payment_date,
                            narration=f'Advance received Rs.{remaining} (over-receipt)'
                        )
                        if updated:
                            messages.success(request, f'Receipt applied to {len(updated)} invoice(s). Rs.{remaining} saved as advance.')
                        else:
                            messages.success(request, f'Rs.{amount} saved as advance (no pending invoices).')
                    elif updated:
                        adv_msg = f' (Rs.{advance_used} from existing advance)' if advance_used > 0 else ''
                        messages.success(request, f'Receipt applied to {len(updated)} invoice(s): {", ".join(updated)}.{adv_msg}')
                    elif advance_used > 0:
                        messages.success(request, f'Rs.{advance_used} advance adjusted against invoices.')
                    else:
                        messages.warning(request, 'No pending invoices found for this customer.')

            return redirect('add_unified_payment')

        except Exception as e:
            import traceback
            print(traceback.format_exc())
            messages.error(request, f'Error: {str(e)}')
            return redirect('add_unified_payment')

    return render(request, 'finance/unified_payment_form.html', {'title': 'Add Payment/Receipt'})


@require_GET
def search_supplier_invoices(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    suppliers = SupplierMaster.objects.filter(
        supplier_name__icontains=query
    ).order_by('supplier_name')[:20]

    results = []
    for supplier in suppliers:
        invoices = InvoiceMaster.objects.filter(supplierid=supplier)
        total_amount  = sum(float(inv.invoice_total or 0) for inv in invoices)
        total_paid    = sum(float(inv.invoice_paid or 0) for inv in invoices)
        balance       = round(total_amount - total_paid)
        pending_count = sum(1 for inv in invoices if round(float(inv.invoice_total or 0) - float(inv.invoice_paid or 0)) > 0)
        advance_bal   = sum(float(a.amount) for a in SupplierAdvance.objects.filter(supplier=supplier, amount__gt=0))
        results.append({
            'supplier_id':      supplier.supplierid,
            'supplier_name':    supplier.supplier_name,
            'total_amount':     round(total_amount),
            'total_paid':       round(total_paid),
            'balance_amount':   balance,
            'pending_invoices': pending_count,
            'advance_balance':  round(advance_bal),
        })
    return JsonResponse(results, safe=False)


@require_GET
def get_supplier_pending_invoices(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)
    supplier_id = request.GET.get('supplier_id', '').strip()
    if not supplier_id or not supplier_id.isdigit():
        return JsonResponse({'error': 'valid supplier_id required'}, status=400)

    invoices = InvoiceMaster.objects.filter(
        supplierid_id=supplier_id
    ).order_by('invoice_date')

    pending = []
    for inv in invoices:
        balance = round(float(inv.invoice_total or 0) - float(inv.invoice_paid or 0))
        if balance > 0:
            pending.append({
                'invoice_no':   inv.invoice_no,
                'invoice_date': inv.invoice_date.strftime('%d-%m-%Y') if inv.invoice_date else '',
                'total_amount': round(float(inv.invoice_total or 0)),
                'paid_amount':  round(float(inv.invoice_paid or 0)),
                'balance':      balance,
                'status':       inv.payment_status,
            })

    total_balance = sum(i['balance'] for i in pending)
    advance_bal   = sum(float(a.amount) for a in SupplierAdvance.objects.filter(supplier_id=supplier_id, amount__gt=0))
    return JsonResponse({'invoices': pending, 'total_balance': total_balance, 'advance_balance': round(advance_bal)})


@require_GET
def get_customer_pending_invoices(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)
    customer_id = request.GET.get('customer_id', '').strip()
    if not customer_id or not customer_id.isdigit():
        return JsonResponse({'error': 'valid customer_id required'}, status=400)

    invoices = SalesInvoiceMaster.objects.filter(
        customerid_id=customer_id
    ).order_by('sales_invoice_date')

    pending = []
    for inv in invoices:
        balance = round(float(inv.sales_invoice_total or 0) - float(inv.sales_invoice_paid or 0))
        if balance > 0:
            pending.append({
                'invoice_no':   inv.sales_invoice_no,
                'invoice_date': inv.sales_invoice_date.strftime('%d-%m-%Y') if inv.sales_invoice_date else '',
                'total_amount': round(float(inv.sales_invoice_total or 0)),
                'paid_amount':  round(float(inv.sales_invoice_paid or 0)),
                'balance':      balance,
                'status':       inv.payment_status,
            })

    total_balance = sum(i['balance'] for i in pending)
    advance_bal   = sum(float(a.amount) for a in CustomerAdvance.objects.filter(customer_id=customer_id, amount__gt=0))
    return JsonResponse({'invoices': pending, 'total_balance': total_balance, 'advance_balance': round(advance_bal)})


@require_GET
def search_customer_invoices(request):
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'login required'}, status=401)
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse([], safe=False)

    customers = CustomerMaster.objects.filter(
        models.Q(customer_name__icontains=query) |
        models.Q(customer_mobile__icontains=query)
    ).order_by('customer_name')[:20]

    results = []
    for customer in customers:
        invoices = SalesInvoiceMaster.objects.filter(customerid=customer)
        total_amount  = sum(float(inv.sales_invoice_total or 0) for inv in invoices)
        total_paid    = sum(float(inv.sales_invoice_paid or 0) for inv in invoices)
        balance       = round(total_amount - total_paid)
        pending_count = sum(1 for inv in invoices if round(float(inv.sales_invoice_total or 0) - float(inv.sales_invoice_paid or 0)) > 0)
        advance_bal   = sum(float(a.amount) for a in CustomerAdvance.objects.filter(customer=customer, amount__gt=0))
        results.append({
            'customer_id':      customer.customerid,
            'customer_name':    customer.customer_name,
            'total_amount':     round(total_amount),
            'total_paid':       round(total_paid),
            'balance_amount':   balance,
            'pending_invoices': pending_count,
            'advance_balance':  round(advance_bal),
        })
    return JsonResponse(results, safe=False)


@login_required
def advance_ledger_view(request):
    party_type  = request.GET.get('party_type', 'supplier')
    party_id    = request.GET.get('party_id')

    entries = AdvanceLedger.objects.none()
    party   = None
    advance_balance = 0

    if party_type == 'supplier' and party_id:
        try:
            party = SupplierMaster.objects.get(supplierid=party_id)
            entries = AdvanceLedger.objects.filter(party_type='supplier', supplier=party)
            advance_balance = sum(float(a.amount) for a in SupplierAdvance.objects.filter(supplier=party, amount__gt=0))
        except SupplierMaster.DoesNotExist:
            pass
    elif party_type == 'customer' and party_id:
        try:
            party = CustomerMaster.objects.get(customerid=party_id)
            entries = AdvanceLedger.objects.filter(party_type='customer', customer=party)
            advance_balance = sum(float(a.amount) for a in CustomerAdvance.objects.filter(customer=party, amount__gt=0))
        except CustomerMaster.DoesNotExist:
            pass

    suppliers = SupplierMaster.objects.order_by('supplier_name')
    customers = CustomerMaster.objects.order_by('customer_name')

    return render(request, 'finance/advance_ledger.html', {
        'entries': entries,
        'party': party,
        'party_type': party_type,
        'advance_balance': advance_balance,
        'suppliers': suppliers,
        'customers': customers,
    })
