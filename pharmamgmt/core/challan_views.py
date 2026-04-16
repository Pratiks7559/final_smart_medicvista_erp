from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
from core.year_filter_utils import apply_year_filter

@login_required
def supplier_challan_list(request):
    """View for supplier challan list"""
    from core.models import Challan1, SupplierMaster
    from django.core.paginator import Paginator
    
    # Only show challans that haven't been invoiced yet
    challans = Challan1.objects.select_related('supplier').filter(is_invoiced=False).order_by('-challan_date', '-challan_id')
    challans = apply_year_filter(challans, request, 'challan_date')
    suppliers = SupplierMaster.objects.all().order_by('supplier_name')
    
    # Pagination
    paginator = Paginator(challans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Supplier Challan List',
        'challans': page_obj,
        'suppliers': suppliers,
        'page_obj': page_obj
    }
    return render(request, 'challan/supplier_challan_list.html', context)

@login_required
def add_supplier_challan(request):
    """View for adding supplier challan with products"""
    from core.models import SupplierMaster, ProductMaster, Challan1, SupplierChallanMaster
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.db import transaction
    import json
    from decimal import Decimal
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                challan_no = request.POST.get('challan_no')
                challan_date = request.POST.get('challan_date')
                supplier_id = request.POST.get('supplierid')
                transport_charges = Decimal(request.POST.get('transport_charges', 0))
                challan_total = Decimal(request.POST.get('challan_total', 0))
                products_data = json.loads(request.POST.get('products_data', '[]'))
                
                if not products_data:
                    messages.error(request, 'Please add at least one product')
                    return redirect('add_supplier_challan')
                
                supplier = SupplierMaster.objects.get(supplierid=supplier_id)
                
                challan = Challan1.objects.create(
                    challan_no=challan_no,
                    challan_date=challan_date,
                    supplier=supplier,
                    challan_total=float(challan_total),
                    transport_charges=float(transport_charges),
                    challan_paid=0.0
                )
                
                for product_data in products_data:
                    from core.models import PurchaseMaster, SaleRateMaster
                    
                    product = ProductMaster.objects.get(productid=product_data['productid'])
                    
                    rate = Decimal(product_data.get('challan_rate', 0))
                    qty = Decimal(product_data.get('quantity', 0))
                    discount = Decimal(product_data.get('discount', 0))
                    cgst = Decimal(product_data.get('cgst', 2.5))
                    sgst = Decimal(product_data.get('sgst', 2.5))
                    batch_no = product_data.get('batch_no', '')
                    expiry = product_data.get('expiry', '')
                    
                    subtotal = rate * qty
                    after_discount = subtotal - discount
                    cgst_amount = (after_discount * cgst) / 100
                    sgst_amount = (after_discount * sgst) / 100
                    total = after_discount + cgst_amount + sgst_amount
                    
                    # Create challan entry - Inventory tracked via StockManager
                    challan_entry = SupplierChallanMaster.objects.create(
                        product_suppliername=supplier,
                        product_challan_id=challan,
                        product_challan_no=challan_no,
                        product_id=product,
                        product_name=product.product_name,
                        product_company=product.product_company,
                        product_packing=product.product_packing,
                        product_batch_no=batch_no,
                        product_expiry=expiry,
                        product_mrp=float(product_data.get('mrp', 0)),
                        product_purchase_rate=float(rate),
                        product_quantity=float(qty),
                        product_free_qty=float(product_data.get('free_qty', 0)),
                        product_scheme=float(product_data.get('scheme', 0)),
                        product_discount=float(discount),
                        cgst=float(cgst),
                        sgst=float(sgst),
                        total_amount=float(total),
                        challan_calculation_mode=product_data.get('calculation_mode', 'flat'),
                        rate_a=float(product_data.get('rate_A', 0) or product_data.get('rate_a', 0) or 0),
                        rate_b=float(product_data.get('rate_B', 0) or product_data.get('rate_b', 0) or 0),
                        rate_c=float(product_data.get('rate_C', 0) or product_data.get('rate_c', 0) or 0)
                    )
                    
                    # REMOVED: Inventory tracking - no longer needed
                    # Inventory is now tracked through PurchaseMaster and SalesMaster tables
                    print(f"✅ SUPPLIER CHALLAN: Added {qty} units of {product.product_name} (Batch: {batch_no}) to challan {challan_no}")
                    
                    # Update sale rates if provided
                    rate_A = product_data.get('rate_A')
                    rate_B = product_data.get('rate_B')
                    rate_C = product_data.get('rate_C')
                    
                    if rate_A or rate_B or rate_C:
                        SaleRateMaster.objects.update_or_create(
                            productid=product,
                            product_batch_no=batch_no,
                            defaults={
                                'rate_A': float(rate_A) if rate_A else 0,
                                'rate_B': float(rate_B) if rate_B else 0,
                                'rate_C': float(rate_C) if rate_C else 0
                            }
                        )
                
                messages.success(request, f'Challan {challan_no} created successfully! Inventory tracking enabled for {len(products_data)} products.')
                return redirect('supplier_challan_list')
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in challan creation: {error_details}")
            messages.error(request, f'Error: {str(e)}')
            return redirect('add_supplier_challan')
    
    suppliers = SupplierMaster.objects.all().order_by('supplier_name')
    products = ProductMaster.objects.all().order_by('product_name')
    
    context = {
        'suppliers': suppliers,
        'products': products,
        'title': 'Add Supplier Challan with Products'
    }
    return render(request, 'challan/supplier_challan_form.html', context)

@login_required
def view_supplier_challan(request, challan_id):
    """View for displaying supplier challan details"""
    from core.models import Challan1, SupplierChallanMaster, SupplierChallanMaster2, SupplierMaster, ProductMaster
    from django.db.models import Sum
    from itertools import chain
    from django.db import transaction
    import json
    from decimal import Decimal
    
    challan = get_object_or_404(Challan1, challan_id=challan_id)
    
    # Handle POST request for editing challan
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Get form data
                challan_date = request.POST.get('challan_date')
                supplier_id = request.POST.get('supplier')
                transport_charges = Decimal(request.POST.get('transport_charges', 0))
                products_data = json.loads(request.POST.get('products_data', '[]'))
                
                if not products_data:
                    return JsonResponse({'success': False, 'error': 'Please add at least one product'})
                
                # Update challan basic info
                supplier = SupplierMaster.objects.get(supplierid=supplier_id)
                challan.challan_date = challan_date
                challan.supplier = supplier
                challan.transport_charges = float(transport_charges)
                
                # Calculate new total
                products_total = sum(
                    Decimal(p.get('purchase_rate', 0)) * Decimal(p.get('quantity', 0)) - 
                    Decimal(p.get('discount', 0)) + 
                    (Decimal(p.get('purchase_rate', 0)) * Decimal(p.get('quantity', 0)) - Decimal(p.get('discount', 0))) * 
                    (Decimal(p.get('cgst', 0)) + Decimal(p.get('sgst', 0))) / 100
                    for p in products_data
                )
                challan.challan_total = float(products_total + transport_charges)
                challan.save()
                
                # Delete existing products
                SupplierChallanMaster.objects.filter(product_challan_id=challan).delete()
                
                # Add new products
                for product_data in products_data:
                    product = ProductMaster.objects.get(productid=product_data['productid'])
                    
                    rate = Decimal(product_data.get('purchase_rate', 0))
                    qty = Decimal(product_data.get('quantity', 0))
                    discount = Decimal(product_data.get('discount', 0))
                    cgst = Decimal(product_data.get('cgst', 2.5))
                    sgst = Decimal(product_data.get('sgst', 2.5))
                    
                    subtotal = rate * qty
                    after_discount = subtotal - discount
                    cgst_amount = (after_discount * cgst) / 100
                    sgst_amount = (after_discount * sgst) / 100
                    total = after_discount + cgst_amount + sgst_amount
                    
                    SupplierChallanMaster.objects.create(
                        product_suppliername=supplier,
                        product_challan_id=challan,
                        product_challan_no=challan.challan_no,
                        product_id=product,
                        product_name=product.product_name,
                        product_company=product.product_company,
                        product_packing=product.product_packing,
                        product_batch_no=product_data.get('batch_no', ''),
                        product_expiry=product_data.get('expiry', ''),
                        product_mrp=float(product_data.get('mrp', 0)),
                        product_purchase_rate=float(rate),
                        product_quantity=float(qty),
                        product_free_qty=float(product_data.get('free_qty', 0)),
                        product_scheme=0,
                        product_discount=float(discount),
                        cgst=float(cgst),
                        sgst=float(sgst),
                        total_amount=float(total),
                        challan_calculation_mode='flat',
                        rate_a=float(product_data.get('rate_a', 0)),
                        rate_b=float(product_data.get('rate_b', 0)),
                        rate_c=float(product_data.get('rate_c', 0))
                    )
                
                return JsonResponse({'success': True, 'message': 'Challan updated successfully'})
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR updating supplier challan: {error_details}")
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request - show details
    challan_items_1 = SupplierChallanMaster.objects.filter(product_challan_id=challan).select_related('product_id')
    challan_items_2 = SupplierChallanMaster2.objects.filter(product_challan_id=challan).select_related('product_id')
    challan_items = list(chain(challan_items_1, challan_items_2))
    
    products_total = (challan_items_1.aggregate(total=Sum('total_amount'))['total'] or 0) + (challan_items_2.aggregate(total=Sum('total_amount'))['total'] or 0)
    
    # Calculate summary figures for the bill footer
    subtotal_before_discount = sum(item.product_purchase_rate * item.product_quantity for item in challan_items)
    total_discount = sum(item.product_discount for item in challan_items)
    discount_pct = (total_discount / subtotal_before_discount * 100) if subtotal_before_discount else 0
    total_gst = sum(
        (item.product_purchase_rate * item.product_quantity - item.product_discount) * (item.cgst + item.sgst) / 100
        for item in challan_items
    )
    
    # Get suppliers and products for edit modal
    suppliers = SupplierMaster.objects.all().order_by('supplier_name')
    products = ProductMaster.objects.all().order_by('product_name')
    
    context = {
        'challan': challan,
        'challan_items': challan_items,
        'products_total': products_total,
        'subtotal_before_discount': subtotal_before_discount,
        'total_discount': total_discount,
        'discount_pct': discount_pct,
        'total_gst': total_gst,
        'suppliers': suppliers,
        'products': products,
        'title': f'Challan {challan.challan_no}'
    }
    return render(request, 'challan/supplier_challan_detail.html', context)

@login_required
def print_purchase_receipt(request, challan_id):
    """Print purchase receipt"""
    from core.models import Challan1, SupplierChallanMaster, SupplierChallanMaster2
    from django.db.models import Sum
    from itertools import chain
    
    challan = get_object_or_404(Challan1, challan_id=challan_id)
    challan_items_1 = SupplierChallanMaster.objects.filter(product_challan_id=challan).select_related('product_id')
    challan_items_2 = SupplierChallanMaster2.objects.filter(product_challan_id=challan).select_related('product_id')
    challan_items = list(chain(challan_items_1, challan_items_2))
    
    subtotal = challan_items.aggregate(total=Sum('total_amount'))['total'] or 0
    total_discount = sum(item.product_discount for item in challan_items)
    cgst_total = sum(item.total_amount * item.cgst / 100 for item in challan_items)
    sgst_total = sum(item.total_amount * item.sgst / 100 for item in challan_items)
    
    context = {
        'challan': challan,
        'challan_items': challan_items,
        'subtotal': subtotal,
        'total_discount': total_discount,
        'cgst_total': cgst_total,
        'sgst_total': sgst_total,
        'grand_total': subtotal + challan.transport_charges
    }
    return render(request, 'challan/print_purchase_receipt.html', context)

@login_required
@require_POST
def delete_supplier_challan(request, challan_id):
    """Delete supplier challan"""
    from core.models import Challan1
    from django.db import transaction
    
    try:
        with transaction.atomic():
            challan = get_object_or_404(Challan1, challan_id=challan_id)
            challan_no = challan.challan_no
            challan.delete()
            return JsonResponse({'success': True, 'message': f'Challan {challan_no} deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# Customer Challan Views
@login_required
def customer_challan_list(request):
    """View for customer challan list - only show non-invoiced challans"""
    from core.models import CustomerChallan, InvoiceSeries
    from datetime import datetime
    from django.core.paginator import Paginator
    
    # Only show challans that haven't been invoiced yet
    challans = CustomerChallan.objects.select_related('customer_name').filter(is_invoiced=False)
    challans = apply_year_filter(challans, request, 'customer_challan_date')
    
    # Apply date filters
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    search_query = request.GET.get('search', '')
    
    if from_date:
        try:
            challans = challans.filter(customer_challan_date__gte=from_date)
        except:
            pass
    
    if to_date:
        try:
            challans = challans.filter(customer_challan_date__lte=to_date)
        except:
            pass
    
    if search_query:
        challans = challans.filter(
            Q(customer_challan_no__icontains=search_query) |
            Q(customer_name__customer_name__icontains=search_query)
        )
    
    challans = challans.order_by('-customer_challan_date', '-customer_challan_id')
    
    # Pagination
    paginator = Paginator(challans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all active invoice series for the dropdown
    invoice_series = InvoiceSeries.objects.filter(is_active=True).order_by('series_name')
    
    context = {
        'title': 'Customer Challan List',
        'challans': page_obj,
        'invoice_series': invoice_series,
        'from_date': from_date,
        'to_date': to_date,
        'search_query': search_query,
        'page_obj': page_obj
    }
    return render(request, 'challan/customer_challan_list.html', context)

@login_required
def add_customer_challan(request):
    """View for adding customer challan with products"""
    from core.models import CustomerMaster, ProductMaster, CustomerChallan, CustomerChallanMaster, InvoiceSeries
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.db import transaction
    import json
    from decimal import Decimal
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                challan_date = request.POST.get('challan_date')
                customer_id = request.POST.get('customer_id')
                series_id = request.POST.get('challan_series')
                transport_charges = Decimal(request.POST.get('transport_charges', 0))
                products_data = json.loads(request.POST.get('products_data', '[]'))
                
                if not products_data:
                    messages.error(request, 'Please add at least one product')
                    return redirect('add_customer_challan')
                
                customer = CustomerMaster.objects.get(customerid=customer_id)
                
                # Get series and generate challan number with date
                series = None
                from datetime import datetime
                from core.models import ChallanSeries
                
                if series_id:
                    series = ChallanSeries.objects.get(series_id=series_id)
                    series_name = series.series_name
                    
                    # Parse challan date
                    challan_date_obj = datetime.strptime(challan_date, '%Y-%m-%d')
                    date_str = challan_date_obj.strftime('%d%m%Y')
                    
                    # Find last challan with same series and date
                    prefix = f'{series_name}{date_str}'
                    last_challan = CustomerChallan.objects.filter(
                        customer_challan_no__startswith=prefix
                    ).order_by('-customer_challan_no').first()
                    
                    if last_challan:
                        # Extract counter from last challan number
                        last_counter = int(last_challan.customer_challan_no[-3:])
                        new_counter = last_counter + 1
                    else:
                        # First challan for this date
                        new_counter = 1
                    
                    challan_no = f'{prefix}{new_counter:03d}'
                else:
                    # Fallback if no series selected
                    challan_date_obj = datetime.strptime(challan_date, '%Y-%m-%d')
                    date_str = challan_date_obj.strftime('%d%m%Y')
                    prefix = f'CH{date_str}'
                    
                    last_challan = CustomerChallan.objects.filter(
                        customer_challan_no__startswith=prefix
                    ).order_by('-customer_challan_no').first()
                    
                    if last_challan:
                        last_counter = int(last_challan.customer_challan_no[-3:])
                        new_counter = last_counter + 1
                    else:
                        new_counter = 1
                    
                    challan_no = f'{prefix}{new_counter:03d}'
                
                # Calculate products total
                products_total = sum(
                    Decimal(p.get('sale_rate', 0)) * Decimal(p.get('quantity', 0)) - 
                    Decimal(p.get('discount', 0)) + 
                    (Decimal(p.get('sale_rate', 0)) * Decimal(p.get('quantity', 0)) - Decimal(p.get('discount', 0))) * 
                    (Decimal(p.get('cgst', 0)) + Decimal(p.get('sgst', 0))) / 100
                    for p in products_data
                )
                challan_total = products_total + transport_charges
                
                challan = CustomerChallan.objects.create(
                    customer_challan_no=challan_no,
                    customer_challan_date=challan_date,
                    customer_name=customer,
                    challan_series=series,
                    customer_transport_charges=float(transport_charges),
                    challan_total=float(challan_total),
                    challan_invoice_paid=0.0
                )
                
                for product_data in products_data:
                    product = ProductMaster.objects.get(productid=product_data['productid'])
                    
                    rate = Decimal(product_data.get('sale_rate', 0))
                    qty = Decimal(product_data.get('quantity', 0))
                    discount = Decimal(product_data.get('discount', 0))
                    cgst = Decimal(product_data.get('cgst', 2.5))
                    sgst = Decimal(product_data.get('sgst', 2.5))
                    batch_no = product_data.get('batch_no', '')
                    expiry = product_data.get('expiry', '')
                    
                    subtotal = rate * qty
                    after_discount = subtotal - discount
                    cgst_amount = (after_discount * cgst) / 100
                    sgst_amount = (after_discount * sgst) / 100
                    total = after_discount + cgst_amount + sgst_amount
                    
                    CustomerChallanMaster.objects.create(
                        customer_challan_id=challan,
                        customer_challan_no=challan_no,
                        customer_name=customer,
                        product_id=product,
                        product_name=product.product_name,
                        product_company=product.product_company,
                        product_packing=product.product_packing,
                        product_batch_no=batch_no,
                        product_expiry=expiry,
                        product_mrp=float(product_data.get('mrp', 0)),
                        sale_rate=float(rate),
                        sale_quantity=float(qty),
                        sale_free_qty=float(product_data.get('free_qty', 0)),
                        sale_discount=float(discount),
                        sale_cgst=float(cgst),
                        sale_sgst=float(sgst),
                        sale_total_amount=float(total),
                        rate_applied=product_data.get('rate_applied', 'NA')
                    )
                    
                    # REMOVED: Inventory tracking - no longer needed
                    # Stock is now tracked through SalesMaster table
                    print(f"✅ CUSTOMER CHALLAN: Added {qty} units of {product.product_name} (Batch: {batch_no}) to challan {challan_no}")
                
                messages.success(request, f'Customer Challan {challan_no} created successfully! Inventory updated.')
                return redirect('view_customer_challan', challan_id=challan.customer_challan_id)
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in customer challan creation: {error_details}")
            messages.error(request, f'Error: {str(e)}')
            return redirect('add_customer_challan')
    
    from core.models import ChallanSeries
    customers = CustomerMaster.objects.all().order_by('customer_name')
    products = ProductMaster.objects.all().order_by('product_name')
    invoice_series = ChallanSeries.objects.filter(is_active=True).order_by('series_name')
    
    context = {
        'customers': customers,
        'products': products,
        'invoice_series': invoice_series,
        'title': 'Add Customer Challan with Products'
    }
    return render(request, 'challan/customer_challan_form.html', context)

@login_required
def view_customer_challan(request, challan_id):
    """View for displaying customer challan details"""
    from core.models import CustomerChallan, CustomerChallanMaster, CustomerChallanMaster2, CustomerMaster, ProductMaster, ChallanSeries
    from django.db.models import Sum
    from itertools import chain
    from django.db import transaction
    import json
    from decimal import Decimal
    
    challan = get_object_or_404(CustomerChallan, customer_challan_id=challan_id)
    
    # Handle POST request for editing challan
    if request.method == 'POST':
        try:
            with transaction.atomic():
                challan_date = request.POST.get('challan_date')
                customer_id = request.POST.get('customer_name')
                transport_charges = Decimal(request.POST.get('transport_charges', 0))
                new_challan_no = request.POST.get('challan_no', '').strip()
                new_series_id = request.POST.get('challan_series_id', '').strip()
                products_data = json.loads(request.POST.get('products_data', '[]'))
                
                if not products_data:
                    return JsonResponse({'success': False, 'error': 'Please add at least one product'})
                
                customer = CustomerMaster.objects.get(customerid=customer_id)
                
                # Handle challan number change
                old_challan_no = challan.customer_challan_no
                if new_challan_no and new_challan_no != old_challan_no:
                    if CustomerChallan.objects.filter(customer_challan_no=new_challan_no).exclude(customer_challan_id=challan_id).exists():
                        return JsonResponse({'success': False, 'error': f'Challan number {new_challan_no} already exists'})
                    # Update challan number in all related records
                    CustomerChallanMaster.objects.filter(customer_challan_id=challan).update(customer_challan_no=new_challan_no)
                    challan.customer_challan_no = new_challan_no
                
                # Handle series change
                if new_series_id:
                    try:
                        challan.challan_series = ChallanSeries.objects.get(series_id=new_series_id)
                    except ChallanSeries.DoesNotExist:
                        pass
                
                challan.customer_challan_date = challan_date
                challan.customer_name = customer
                challan.customer_transport_charges = float(transport_charges)
                
                # Recalculate total
                products_total = sum(
                    Decimal(p.get('rate', 0)) * Decimal(p.get('quantity', 0)) -
                    Decimal(p.get('discount', 0)) +
                    (Decimal(p.get('rate', 0)) * Decimal(p.get('quantity', 0)) - Decimal(p.get('discount', 0))) *
                    (Decimal(p.get('cgst', 0)) + Decimal(p.get('sgst', 0))) / 100
                    for p in products_data
                )
                challan.challan_total = float(products_total + transport_charges)
                challan.save()
                
                # Replace products
                CustomerChallanMaster.objects.filter(customer_challan_id=challan).delete()
                
                for product_data in products_data:
                    product = ProductMaster.objects.get(productid=product_data['productid'])
                    rate = Decimal(product_data.get('rate', 0))
                    qty = Decimal(product_data.get('quantity', 0))
                    discount = Decimal(product_data.get('discount', 0))
                    cgst = Decimal(product_data.get('cgst', 2.5))
                    sgst = Decimal(product_data.get('sgst', 2.5))
                    subtotal = rate * qty
                    after_discount = subtotal - discount
                    total = after_discount + (after_discount * cgst / 100) + (after_discount * sgst / 100)
                    
                    CustomerChallanMaster.objects.create(
                        customer_challan_id=challan,
                        customer_challan_no=challan.customer_challan_no,
                        customer_name=customer,
                        product_id=product,
                        product_name=product.product_name,
                        product_company=product.product_company,
                        product_packing=product.product_packing,
                        product_batch_no=product_data.get('batch_no', ''),
                        product_expiry=product_data.get('expiry', ''),
                        product_mrp=float(product_data.get('mrp', 0)),
                        sale_rate=float(rate),
                        sale_quantity=float(qty),
                        sale_free_qty=float(product_data.get('free_qty', 0)),
                        sale_discount=float(discount),
                        sale_cgst=float(cgst),
                        sale_sgst=float(sgst),
                        sale_total_amount=float(total),
                        rate_applied='NA'
                    )
                
                return JsonResponse({'success': True, 'message': 'Challan updated successfully'})
                
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET request
    challan_items_1 = CustomerChallanMaster.objects.filter(customer_challan_id=challan).select_related('product_id')
    challan_items_2 = CustomerChallanMaster2.objects.filter(customer_challan_id=challan).select_related('product_id')
    challan_items = list(chain(challan_items_1, challan_items_2))
    
    grand_total = (challan_items_1.aggregate(total=Sum('sale_total_amount'))['total'] or 0) + (challan_items_2.aggregate(total=Sum('sale_total_amount'))['total'] or 0)
    final_total = grand_total + (challan.customer_transport_charges or 0)
    
    # Calculate summary figures for the bill footer
    subtotal_before_discount = sum(item.sale_rate * item.sale_quantity for item in challan_items)
    total_discount = sum(item.sale_discount for item in challan_items)
    discount_pct = (total_discount / subtotal_before_discount * 100) if subtotal_before_discount else 0
    total_gst = sum(
        (item.sale_rate * item.sale_quantity - item.sale_discount) * (item.sale_cgst + item.sale_sgst) / 100
        for item in challan_items
    )
    
    customers = CustomerMaster.objects.all().order_by('customer_name')
    products = ProductMaster.objects.all().order_by('product_name')
    challan_series = ChallanSeries.objects.filter(is_active=True).order_by('series_name')
    
    context = {
        'challan': challan,
        'challan_items': challan_items,
        'grand_total': grand_total,
        'final_total': final_total,
        'subtotal_before_discount': subtotal_before_discount,
        'total_discount': total_discount,
        'discount_pct': discount_pct,
        'total_gst': total_gst,
        'customers': customers,
        'products': products,
        'challan_series': challan_series,
        'title': f'Challan {challan.customer_challan_no}'
    }
    return render(request, 'challan/customer_challan_detail.html', context)

@login_required
@require_POST
def delete_customer_challan(request, challan_id):
    """Delete customer challan"""
    from core.models import CustomerChallan
    from django.db import transaction
    
    try:
        with transaction.atomic():
            challan = get_object_or_404(CustomerChallan, customer_challan_id=challan_id)
            challan_no = challan.customer_challan_no
            challan.delete()
            return JsonResponse({'success': True, 'message': f'Challan {challan_no} deleted successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_next_challan_number(request):
    """API endpoint to get next challan number preview"""
    from core.models import CustomerChallan
    from datetime import datetime
    
    try:
        series_name = request.GET.get('series_name', '')
        date_str = request.GET.get('date', '')
        
        if not series_name or not date_str:
            return JsonResponse({'success': False, 'error': 'Missing parameters'})
        
        # Parse date
        challan_date = datetime.strptime(date_str, '%Y-%m-%d')
        date_formatted = challan_date.strftime('%d%m%Y')
        
        # Generate prefix
        prefix = f'{series_name}{date_formatted}'
        
        # Find last challan with same prefix
        last_challan = CustomerChallan.objects.filter(
            customer_challan_no__startswith=prefix
        ).order_by('-customer_challan_no').first()
        
        if last_challan:
            last_counter = int(last_challan.customer_challan_no[-3:])
            new_counter = last_counter + 1
        else:
            new_counter = 1
        
        challan_number = f'{prefix}{new_counter:03d}'
        
        return JsonResponse({
            'success': True,
            'challan_number': challan_number
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def add_challan_series(request):
    """Add new challan series"""
    from core.models import ChallanSeries
    
    if request.method == 'POST':
        series_name = request.POST.get('series_name', '').strip().upper()
        
        if not series_name:
            return JsonResponse({'success': False, 'error': 'Series name is required'})
        
        if len(series_name) > 10:
            return JsonResponse({'success': False, 'error': 'Series name must be 10 characters or less'})
        
        try:
            if ChallanSeries.objects.filter(series_name=series_name).exists():
                return JsonResponse({'success': False, 'error': 'Series already exists'})
            
            series = ChallanSeries.objects.create(
                series_name=series_name,
                is_active=True
            )
            
            return JsonResponse({
                'success': True,
                'series_id': series.series_id,
                'series_name': series.series_name,
                'message': f'Series "{series_name}" added successfully!'
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})



@login_required
def get_customer_challans_api(request):
    """API to get customer challans for pull challan dialog"""
    from core.models import CustomerChallan, CustomerChallanMaster
    from django.db.models import Count
    
    try:
        customer_id = request.GET.get('customer_id')
        if not customer_id:
            return JsonResponse({'success': False, 'error': 'Customer ID required'})
        
        # Get challans that have entries in CustomerChallanMaster (not yet moved to CustomerChallanMaster2)
        # This ensures that once all products from a challan are invoiced and moved to CustomerChallanMaster2,
        # the challan won't appear in the Pull Challan list anymore
        challan_ids_with_entries = CustomerChallanMaster.objects.filter(
            customer_name_id=customer_id
        ).values_list('customer_challan_id', flat=True).distinct()
        
        challans = CustomerChallan.objects.filter(
            customer_challan_id__in=challan_ids_with_entries,
            customer_name_id=customer_id
        ).annotate(
            product_count=Count('customerchallanmaster')
        ).order_by('-customer_challan_date')
        
        challan_list = []
        for challan in challans:
            challan_list.append({
                'id': challan.customer_challan_id,
                'challan_no': challan.customer_challan_no,
                'date': challan.customer_challan_date.strftime('%d-%m-%Y'),
                'product_count': challan.product_count,
                'total': f"{challan.challan_total:.2f}"
            })
        
        return JsonResponse({
            'success': True,
            'challans': challan_list
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def get_challan_products_api(request):
    """API to get products from selected challans"""
    from core.models import CustomerChallanMaster
    import json
    
    try:
        data = json.loads(request.body)
        challan_ids = data.get('challan_ids', [])
        
        if not challan_ids:
            return JsonResponse({'success': False, 'error': 'No challans selected'})
        
        # Get all products from selected challans (only from CustomerChallanMaster, not CustomerChallanMaster2)
        # This ensures that once products are moved to CustomerChallanMaster2, they won't appear in Pull Challan list
        challan_items = CustomerChallanMaster.objects.filter(
            customer_challan_id__in=challan_ids
        ).select_related('product_id', 'customer_challan_id')
        
        products = []
        for item in challan_items:
            products.append({
                'product_id': item.product_id.productid,
                'batch_no': item.product_batch_no,
                'expiry': item.product_expiry,
                'mrp': item.product_mrp,
                'rate': item.sale_rate,
                'quantity': item.sale_quantity,
                'free_qty': item.sale_free_qty,
                'discount': item.sale_discount,
                'cgst': item.sale_cgst,
                'sgst': item.sale_sgst,
                'challan_no': item.customer_challan_no,
                'challan_date': item.customer_challan_id.customer_challan_date.strftime('%Y-%m-%d')
            })
        
        return JsonResponse({
            'success': True,
            'products': products
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@require_POST
def create_customer_invoice_from_challans(request):
    """Create sales challan invoice from selected customer challans"""
    from core.models import CustomerChallan, SalesInvoiceMaster, InvoiceSeries, SalesMaster, CustomerChallanMaster
    from django.db import transaction
    import json
    
    try:
        data = json.loads(request.body)
        series_id = data.get('series_id')
        invoice_date = data.get('invoice_date')
        challan_ids = data.get('challan_ids', [])
        
        if not series_id or not invoice_date or not challan_ids:
            return JsonResponse({'success': False, 'error': 'Missing required fields'})
        
        with transaction.atomic():
            # Get invoice series and generate invoice number
            try:
                series = InvoiceSeries.objects.get(series_id=series_id, is_active=True)
                invoice_no = series.get_next_invoice_number()
            except InvoiceSeries.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid invoice series'})
            
            # Get selected challans
            challans = CustomerChallan.objects.filter(customer_challan_id__in=challan_ids, is_invoiced=False)
            if not challans.exists():
                return JsonResponse({'success': False, 'error': 'No valid challans found or already invoiced'})
            
            # Check if all challans are from same customer
            customers = set(challan.customer_name.customerid for challan in challans)
            if len(customers) > 1:
                return JsonResponse({'success': False, 'error': 'All challans must be from the same customer'})
            
            customer = challans.first().customer_name
            
            # Create sales invoice
            sales_invoice = SalesInvoiceMaster.objects.create(
                sales_invoice_no=invoice_no,
                sales_invoice_date=invoice_date,
                customerid=customer,
                invoice_series=series,
                sales_transport_charges=0,
                sales_invoice_paid=0.0
            )
            
            # Copy challan items to sales master
            for challan in challans:
                challan_items = CustomerChallanMaster.objects.filter(customer_challan_id=challan)
                for item in challan_items:
                    SalesMaster.objects.create(
                        sales_invoice_no=sales_invoice,
                        customerid=customer,
                        productid=item.product_id,
                        product_name=item.product_name,
                        product_company=item.product_company,
                        product_packing=item.product_packing,
                        product_batch_no=item.product_batch_no,
                        product_expiry=item.product_expiry,
                        product_MRP=item.product_mrp,
                        sale_rate=item.sale_rate,
                        sale_quantity=item.sale_quantity,
                        sale_discount=item.sale_discount,
                        sale_cgst=item.sale_cgst,
                        sale_sgst=item.sale_sgst,
                        sale_total_amount=item.sale_total_amount,
                        rate_applied=item.rate_applied
                    )
            
            # Mark selected challans as invoiced
            challans.update(is_invoiced=True)
            
            return JsonResponse({
                'success': True,
                'message': f'Sales Invoice {invoice_no} created successfully from challans!',
                'invoice_number': invoice_no,
                'redirect_url': f'/sales/invoice_detail/{invoice_no}/'
            })
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})














