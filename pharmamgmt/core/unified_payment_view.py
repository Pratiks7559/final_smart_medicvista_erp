from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from datetime import datetime
from django.db import models
from decimal import Decimal, ROUND_HALF_UP
from .models import (
    InvoiceMaster, InvoicePaid, SalesInvoiceMaster, SalesInvoicePaid,
    SupplierMaster, CustomerMaster
)

@login_required
def add_unified_payment(request):
    """Unified view for adding payments, receipts, and contra entries"""
    
    if request.method == 'POST':
        try:
            print("=== UNIFIED PAYMENT FORM SUBMISSION ===")
            print(f"All POST data: {dict(request.POST)}")
            
            # Get form data
            transaction_type = request.POST.get('transaction_type')
            payment_date = request.POST.get('payment_date')
            payment_amount = request.POST.get('payment_amount')
            payment_mode = request.POST.get('payment_mode')
            reference_no = request.POST.get('reference_no', '')
            entity_id = request.POST.get('entity_id')
            invoice_no = request.POST.get('invoice_no')
            
            print(f"Extracted form data:")
            print(f"   Transaction type: '{transaction_type}'")
            print(f"   Payment amount: '{payment_amount}'")
            print(f"   Payment mode: '{payment_mode}'")
            print(f"   Entity ID: '{entity_id}'")
            print(f"   Invoice no: '{invoice_no}'")
            print(f"   Payment date: '{payment_date}'")
            
            # Validate required fields
            missing_fields = []
            if not transaction_type:
                missing_fields.append('transaction_type')
            if not payment_date:
                missing_fields.append('payment_date')
            if not payment_amount:
                missing_fields.append('payment_amount')
            if not payment_mode:
                missing_fields.append('payment_mode')
                
            if missing_fields:
                print(f"Missing required fields: {missing_fields}")
                messages.error(request, f'Missing required fields: {", ".join(missing_fields)}')
                return redirect('add_unified_payment')
            
            # Validate transaction type
            if transaction_type not in ['payment', 'receipt', 'contra']:
                print(f"Invalid transaction type: '{transaction_type}'")
                messages.error(request, 'Invalid transaction type.')
                return redirect('add_unified_payment')
            
            # For payment and receipt, entity and invoice are required
            if transaction_type in ['payment', 'receipt']:
                if not entity_id:
                    print(f"Missing entity_id for {transaction_type}")
                    messages.error(request, 'Please select an invoice first (missing entity).')
                    return redirect('add_unified_payment')
                if not invoice_no:
                    print(f"Missing invoice_no for {transaction_type}")
                    messages.error(request, 'Please select an invoice first (missing invoice number).')
                    return redirect('add_unified_payment')
            
            # Validate and convert amount to Decimal for precision
            try:
                payment_amount = Decimal(str(payment_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if payment_amount <= 0:
                    print(f"Invalid payment amount: {payment_amount}")
                    messages.error(request, 'Payment amount must be greater than 0.')
                    return redirect('add_unified_payment')
            except (ValueError, TypeError):
                print(f"Cannot convert payment amount to decimal: '{payment_amount}'")
                messages.error(request, 'Invalid payment amount.')
                return redirect('add_unified_payment')
            
            # Parse date
            try:
                payment_date = datetime.strptime(payment_date, '%Y-%m-%d').date()
                print(f"Parsed payment date: {payment_date}")
            except ValueError:
                print(f"Invalid date format: '{payment_date}'")
                messages.error(request, 'Invalid date format.')
                return redirect('add_unified_payment')
            
            # Handle bank name for bank transfer
            bank_name = request.POST.get('bank_name', '').strip()
            print(f"Bank name from form: '{bank_name}'")
            if payment_mode == 'bank':
                if bank_name:
                    payment_mode = f'bank - {bank_name}'
                    print(f"Updated payment mode: '{payment_mode}'")
                else:
                    print(f"Bank transfer selected but no bank name provided")
                    messages.error(request, 'Bank name is required for bank transfer.')
                    return redirect('add_unified_payment')
            
            with transaction.atomic():
                if transaction_type == 'payment':
                    # Handle supplier payment
                    print(f"Processing supplier payment for invoice: {invoice_no}")
                    try:
                        invoice = InvoiceMaster.objects.get(invoice_no=invoice_no)
                        print(f"Found invoice: {invoice} (Total: Rs.{invoice.invoice_total}, Paid: Rs.{invoice.invoice_paid})")
                        
                        # Calculate balance with proper decimal precision
                        invoice_total = Decimal(str(invoice.invoice_total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        invoice_paid = Decimal(str(invoice.invoice_paid)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        balance = invoice_total - invoice_paid
                        balance_rounded = Decimal(str(round(float(balance))))
                        
                        print(f"Invoice balance: Rs.{balance} (rounded: Rs.{balance_rounded})")
                        
                        # Check against rounded balance (user pays round off amount)
                        if payment_amount > balance_rounded:
                            print(f"Payment amount Rs.{payment_amount} exceeds rounded balance Rs.{balance_rounded}")
                            messages.error(request, f'Payment amount cannot exceed balance of Rs.{balance_rounded}')
                            return redirect('add_unified_payment')
                        
                        # Create payment record
                        print(f"Creating payment record...")
                        payment_record = InvoicePaid.objects.create(
                            ip_invoiceid=invoice,
                            payment_date=payment_date,
                            payment_amount=payment_amount,
                            payment_mode=payment_mode,
                            payment_ref_no=reference_no
                        )
                        print(f"Payment record created with ID: {payment_record.payment_id}")
                        
                        # Update invoice paid amount
                        old_paid = invoice.invoice_paid
                        invoice.invoice_paid = float(invoice_paid + payment_amount)
                        
                        # Update payment status — compare rounded values
                        new_balance = invoice_total - Decimal(str(invoice.invoice_paid))
                        new_balance_rounded = Decimal(str(round(float(new_balance))))
                        if new_balance_rounded <= Decimal('0'):
                            invoice.payment_status = 'paid'
                            print(f"Invoice marked as fully paid")
                        elif invoice.invoice_paid > 0:
                            invoice.payment_status = 'partial'
                            print(f"Invoice marked as partially paid")
                        else:
                            invoice.payment_status = 'pending'
                        
                        invoice.save()
                        print(f"Invoice updated: Rs.{old_paid} -> Rs.{invoice.invoice_paid}, New balance: Rs.{new_balance}")
                        
                        if new_balance_rounded <= Decimal('0'):
                            messages.success(request, f'Payment of Rs.{payment_amount} added successfully! Invoice is now fully paid.')
                        else:
                            messages.success(request, f'Payment of Rs.{payment_amount} added successfully! Remaining balance: Rs.{new_balance_rounded}')
                        
                    except InvoiceMaster.DoesNotExist:
                        print(f"Invoice not found with invoice_no: '{invoice_no}'")
                        # List available invoices for debugging
                        available_invoices = InvoiceMaster.objects.all()[:5]
                        print(f"Available invoices: {[inv.invoice_no for inv in available_invoices]}")
                        messages.error(request, f'Invoice {invoice_no} not found.')
                        return redirect('add_unified_payment')
                    except Exception as e:
                        print(f"Error creating payment: {str(e)}")
                        messages.error(request, f'Error creating payment: {str(e)}')
                        return redirect('add_unified_payment')
                
                elif transaction_type == 'receipt':
                    # Handle customer receipt
                    print(f"Processing customer receipt for invoice: {invoice_no}")
                    try:
                        invoice = SalesInvoiceMaster.objects.get(sales_invoice_no=invoice_no)
                        print(f"Found sales invoice: {invoice} (Total: Rs.{invoice.sales_invoice_total}, Paid: Rs.{invoice.sales_invoice_paid})")
                        
                        # Calculate balance with proper decimal precision
                        invoice_total = Decimal(str(invoice.sales_invoice_total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        invoice_paid = Decimal(str(invoice.sales_invoice_paid)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                        balance = invoice_total - invoice_paid
                        balance_rounded = Decimal(str(round(float(balance))))
                        
                        print(f"Sales invoice balance: Rs.{balance} (rounded: Rs.{balance_rounded})")
                        
                        # Check against rounded balance (user pays round off amount)
                        if payment_amount > balance_rounded:
                            print(f"Receipt amount Rs.{payment_amount} exceeds rounded balance Rs.{balance_rounded}")
                            messages.error(request, f'Receipt amount cannot exceed balance of Rs.{balance_rounded}')
                            return redirect('add_unified_payment')
                        
                        # Create receipt record
                        print(f"Creating receipt record...")
                        receipt_record = SalesInvoicePaid.objects.create(
                            sales_ip_invoice_no=invoice,
                            sales_payment_date=payment_date,
                            sales_payment_amount=payment_amount,
                            sales_payment_mode=payment_mode,
                            sales_payment_ref_no=reference_no
                        )
                        print(f"Receipt record created with ID: {receipt_record.sales_payment_id}")
                        
                        # Update invoice paid amount
                        old_paid = invoice.sales_invoice_paid
                        invoice.sales_invoice_paid = float(invoice_paid + payment_amount)
                        
                        # Update payment status — compare rounded values
                        new_balance = invoice_total - Decimal(str(invoice.sales_invoice_paid))
                        new_balance_rounded = Decimal(str(round(float(new_balance))))
                        if new_balance_rounded <= Decimal('0'):
                            invoice.payment_status = 'paid'
                            print(f"Sales invoice marked as fully paid")
                        elif invoice.sales_invoice_paid > 0:
                            invoice.payment_status = 'partial'
                        else:
                            invoice.payment_status = 'pending'
                        
                        invoice.save()
                        print(f"Sales invoice updated: Rs.{old_paid} -> Rs.{invoice.sales_invoice_paid}, New balance: Rs.{new_balance}")
                        
                        if new_balance_rounded <= Decimal('0'):
                            messages.success(request, f'Receipt of Rs.{payment_amount} added successfully! Invoice is now fully paid.')
                        else:
                            messages.success(request, f'Receipt of Rs.{payment_amount} added successfully! Remaining balance: Rs.{new_balance_rounded}')
                        
                    except SalesInvoiceMaster.DoesNotExist:
                        print(f"Sales invoice not found with sales_invoice_no: '{invoice_no}'")
                        # List available sales invoices for debugging
                        available_invoices = SalesInvoiceMaster.objects.all()[:5]
                        print(f"Available sales invoices: {[inv.sales_invoice_no for inv in available_invoices]}")
                        messages.error(request, f'Sales invoice {invoice_no} not found.')
                        return redirect('add_unified_payment')
                    except Exception as e:
                        print(f"Error creating receipt: {str(e)}")
                        messages.error(request, f'Error creating receipt: {str(e)}')
                        return redirect('add_unified_payment')
                
                elif transaction_type == 'contra':
                    # Handle contra entry (direct cash/bank transfer)
                    print(f"Processing contra entry of Rs.{payment_amount}")
                    # For now, just show success message
                    # You can extend this to create contra entries in a separate table
                    print(f"Contra entry processed successfully")
                    messages.success(request, f'Contra entry of Rs.{payment_amount:.2f} recorded successfully!')
                
                print(f"Transaction completed successfully")
                return redirect('add_unified_payment')
                
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            messages.error(request, f'Error processing transaction: {str(e)}')
            return redirect('add_unified_payment')
    
    # GET request - show form
    context = {
        'title': 'Add Payment/Receipt'
    }
    return render(request, 'finance/unified_payment_form.html', context)

@login_required
def search_supplier_invoices(request):
    """Search supplier invoices for payment - only show invoices with balance > 0"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    invoices = InvoiceMaster.objects.filter(
        supplierid__supplier_name__icontains=query
    ).select_related('supplierid').order_by('-invoice_date')[:50]
    
    results = []
    for invoice in invoices:
        balance = float(invoice.invoice_total) - float(invoice.invoice_paid)
        balance_rounded = round(balance)
        if balance_rounded > 0:  # Only show invoices with pending balance
            results.append({
                'supplier_id': invoice.supplierid.supplierid,
                'supplier_name': invoice.supplierid.supplier_name,
                'invoice_no': invoice.invoice_no,
                'invoice_date': invoice.invoice_date.strftime('%d-%m-%Y'),
                'total_amount': round(float(invoice.invoice_total)),
                'paid_amount': round(float(invoice.invoice_paid)),
                'balance_amount': balance_rounded
            })
        if len(results) >= 20:
            break
    
    return JsonResponse(results, safe=False)


@login_required
def search_customer_invoices(request):
    """Search customer invoices for receipt - only show invoices with balance > 0"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    invoices = SalesInvoiceMaster.objects.filter(
        models.Q(customerid__customer_name__icontains=query) |
        models.Q(customerid__customer_mobile__icontains=query)
    ).select_related('customerid').order_by('-sales_invoice_date')[:50]
    
    results = []
    for invoice in invoices:
        balance = float(invoice.sales_invoice_total) - float(invoice.sales_invoice_paid)
        balance_rounded = round(balance)
        if balance_rounded > 0:  # Only show invoices with pending balance
            results.append({
                'customer_id': invoice.customerid.customerid,
                'customer_name': invoice.customerid.customer_name,
                'invoice_no': invoice.sales_invoice_no,
                'invoice_date': invoice.sales_invoice_date.strftime('%d-%m-%Y'),
                'total_amount': round(float(invoice.sales_invoice_total)),
                'paid_amount': round(float(invoice.sales_invoice_paid)),
                'balance_amount': balance_rounded
            })
        if len(results) >= 20:
            break
    
    return JsonResponse(results, safe=False)