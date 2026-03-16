import json
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Sum, Q
from .models import ProductMaster, SupplierMaster, PurchaseMaster, SaleRateMaster, InvoiceMaster, SalesMaster, Challan1, SupplierChallanMaster, SupplierChallanMaster2
from .forms import InvoiceForm
from .stock_manager import StockManager
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple file logging for debugging
import os
log_file = os.path.join(os.path.dirname(__file__), 'invoice_debug.log')
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

@login_required
def add_invoice_with_products(request):
    if request.method == 'POST':
        try:
            # Debug: Log the POST data
            logger.info(f"POST data received: {request.POST}")
            
            # Handle form submission
            invoice_form = InvoiceForm(request.POST)
            
            # Debug: Check form validation
            if not invoice_form.is_valid():
                logger.error(f"Invoice form validation errors: {invoice_form.errors}")
                messages.error(request, f"Invoice form validation failed: {invoice_form.errors}")
                # Return to form with errors
                suppliers = SupplierMaster.objects.all().order_by('supplier_name')
                products = ProductMaster.objects.all().order_by('product_name')
                context = {
                    'invoice_form': invoice_form,
                    'suppliers': suppliers,
                    'products': products,
                    'title': 'Add Invoice with Products'
                }
                return render(request, 'purchases/combined_invoice_form.html', context)
            
            # Process products data from JavaScript
            products_data = request.POST.get('products_data')
            challan_flag = request.POST.get('is_from_challan', 'false').lower()
            is_from_challan = challan_flag == 'true'
            is_mixed_mode = challan_flag == 'mixed'
            logger.info(f"Products data received: {products_data}")
            logger.info(f"Challan flag: {challan_flag}")
            
            # Allow invoice creation without products - just log it
            if not products_data or products_data.strip() == '' or products_data.strip() == '[]':
                logger.info("Invoice being created without products - header only")
                products_data = '[]'  # Set empty array for processing
            
            try:
                products = json.loads(products_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                messages.error(request, "Invalid products data format. Please try again.")
                suppliers = SupplierMaster.objects.all().order_by('supplier_name')
                products_list = ProductMaster.objects.all().order_by('product_name')
                context = {
                    'invoice_form': invoice_form,
                    'suppliers': suppliers,
                    'products': products_list,
                    'title': 'Add Invoice with Products'
                }
                return render(request, 'purchases/combined_invoice_form.html', context)
            
            # Filter valid products but allow invoice creation even without products
            valid_products = []
            for product in products:
                try:
                    product_id = product.get('productid')
                    batch_no = str(product.get('batch_no', '')).strip()
                    quantity_val = product.get('quantity', 0)
                    quantity = float(str(quantity_val)) if quantity_val else 0.0
                    
                    if product_id and batch_no and quantity > 0:
                        valid_products.append(product)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error validating product: {e}")
                    continue
            
            # Log if no valid products but continue with invoice creation
            if not valid_products:
                logger.info("Creating invoice without valid products - header only invoice")
                valid_products = []  # Empty list for processing
            
            # Use valid products for processing
            products = valid_products
            
            # Use transaction to ensure data consistency
            with transaction.atomic():
                # Create invoice
                invoice = invoice_form.save(commit=False)
                invoice.invoice_paid = 0
                invoice.save()
                logger.info(f"Invoice created with ID: {invoice.invoiceid}")
                
                total_amount = 0
                products_added = 0
                errors = []
                
                for i, product_data in enumerate(products):
                    if product_data.get('productid'):
                        try:
                            # Get product details
                            product = ProductMaster.objects.get(productid=product_data['productid'])
                            
                            # Validate required fields
                            batch_no = product_data.get('batch_no', '').strip()
                            expiry = product_data.get('expiry', '').strip()
                            
                            if not batch_no:
                                errors.append(f"Row {i+1}: Batch number is required for {product.product_name}")
                                continue
                            
                            if not expiry:
                                errors.append(f"Row {i+1}: Expiry date is required for {product.product_name}")
                                continue
                            
                            # Validate and normalize expiry date to MM-YYYY format
                            try:
                                import re
                                expiry = expiry.strip()
                                
                                # Handle different input formats and convert to MM-YYYY
                                if len(expiry) == 4 and expiry.isdigit():
                                    month = expiry[:2]
                                    year = '20' + expiry[2:4]
                                    expiry = f"{month}-{year}"
                                elif len(expiry) == 6 and expiry.isdigit():
                                    month = expiry[:2]
                                    year = expiry[2:6]
                                    expiry = f"{month}-{year}"
                                elif '/' in expiry:
                                    expiry = expiry.replace('/', '-')
                                elif len(expiry) == 7 and expiry.count('-') == 1:
                                    pass
                                elif not expiry:
                                    raise ValueError("Empty expiry date")
                                else:
                                    digits = re.sub(r'[^0-9]', '', expiry)
                                    if len(digits) == 4:
                                        expiry = f"{digits[:2]}-20{digits[2:4]}"
                                    elif len(digits) == 6:
                                        expiry = f"{digits[:2]}-{digits[2:6]}"
                                    else:
                                        raise ValueError("Invalid format")
                                
                                if not re.match(r'^(0[1-9]|1[0-2])-\d{4}$', expiry):
                                    raise ValueError("Invalid MM-YYYY format")
                                
                                month, year = expiry.split('-')
                                month = int(month)
                                year = int(year)
                                
                                if int(month) < 1 or int(month) > 12:
                                    raise ValueError("Invalid month")
                                if int(year) < 2020 or int(year) > 2100:
                                    raise ValueError("Invalid year")
                                
                            except (ValueError, IndexError) as e:
                                errors.append(f"Row {i+1}: Invalid expiry date format for {product.product_name}. Use MM-YYYY format (e.g., 12-2025). Got: '{product_data.get('expiry', '')}'. Error: {str(e)}")
                                continue
                            
                            # Convert and validate numeric fields
                            try:
                                mrp_val = product_data.get('mrp', 0)
                                purchase_rate_val = product_data.get('purchase_rate', 0)
                                quantity_val = product_data.get('quantity', 0)
                                free_qty_val = product_data.get('free_qty', 0)
                                print(f"DEBUG: free_qty_val from form = {free_qty_val}, type = {type(free_qty_val)}")
                                scheme_val = product_data.get('scheme', 0)
                                discount_val = product_data.get('discount', 0)
                                cgst_val = product_data.get('cgst', 0)
                                sgst_val = product_data.get('sgst', 0)
                                
                                # Convert to float, handling string values
                                mrp = float(str(mrp_val)) if mrp_val else 0.0
                                purchase_rate = float(str(purchase_rate_val)) if purchase_rate_val else 0.0
                                quantity = float(str(quantity_val)) if quantity_val else 0.0
                                free_qty = float(str(free_qty_val)) if free_qty_val else 0.0
                                scheme = float(str(scheme_val)) if scheme_val else 0.0
                                discount = float(str(discount_val)) if discount_val else 0.0
                                cgst = float(str(cgst_val)) if cgst_val else 0.0
                                sgst = float(str(sgst_val)) if sgst_val else 0.0
                            except (ValueError, TypeError) as e:
                                errors.append(f"Row {i+1}: Invalid numeric values for {product.product_name}: {e}")
                                continue
                            
                            if float(quantity) <= 0:
                                errors.append(f"Row {i+1}: Quantity must be greater than 0 for {product.product_name}")
                                continue
                            
                            if float(purchase_rate) <= 0:
                                errors.append(f"Row {i+1}: Purchase rate must be greater than 0 for {product.product_name}")
                                continue
                            
                            # Create purchase entry
                            purchase = PurchaseMaster()
                            purchase.product_supplierid = invoice.supplierid
                            purchase.product_invoiceid = invoice
                            purchase.product_invoice_no = invoice.invoice_no
                            purchase.productid = product
                            purchase.product_name = product.product_name
                            purchase.product_company = product.product_company
                            purchase.product_packing = product.product_packing
                            purchase.product_batch_no = batch_no
                            purchase.product_expiry = expiry
                            purchase.product_MRP = mrp
                            purchase.product_purchase_rate = purchase_rate
                            purchase.product_quantity = quantity
                            purchase.product_free_qty = free_qty
                            print(f"DEBUG: Saving purchase with free_qty = {free_qty}")
                            purchase.product_scheme = scheme
                            purchase.product_discount_got = discount
                            purchase.CGST = cgst
                            purchase.SGST = sgst
                            purchase.purchase_calculation_mode = product_data.get('calculation_mode', 'flat')
                            
                            # Challan reference fields
                            challan_no = product_data.get('challan_no', '')
                            challan_date_str = product_data.get('challan_date', '')
                            
                            logger.info(f"Challan data received: challan_no={challan_no}, challan_date={challan_date_str}")
                            
                            if challan_no and str(challan_no).strip():
                                purchase.source_challan_no = str(challan_no).strip()
                                logger.info(f"Set source_challan_no: {purchase.source_challan_no}")
                            else:
                                purchase.source_challan_no = None
                            
                            if challan_date_str and str(challan_date_str).strip():
                                try:
                                    from datetime import datetime
                                    date_str = str(challan_date_str).strip()
                                    # Try multiple date formats
                                    for fmt in ['%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y']:
                                        try:
                                            purchase.source_challan_date = datetime.strptime(date_str, fmt).date()
                                            logger.info(f"Set source_challan_date: {purchase.source_challan_date}")
                                            break
                                        except ValueError:
                                            continue
                                except Exception as e:
                                    logger.warning(f"Error parsing challan date '{challan_date_str}': {e}")
                                    purchase.source_challan_date = None
                            else:
                                purchase.source_challan_date = None
                            
                            # Optional rate fields - store in PurchaseMaster
                            try:
                                rate_a_val = product_data.get('rate_a', 0) or product_data.get('rate_A', 0)
                                rate_b_val = product_data.get('rate_b', 0) or product_data.get('rate_B', 0)
                                rate_c_val = product_data.get('rate_c', 0) or product_data.get('rate_C', 0)
                                
                                purchase.rate_a = float(str(rate_a_val)) if rate_a_val else 0.0
                                purchase.rate_b = float(str(rate_b_val)) if rate_b_val else 0.0
                                purchase.rate_c = float(str(rate_c_val)) if rate_c_val else 0.0
                                
                                logger.info(f"Setting rates for {product.product_name}: A={purchase.rate_a}, B={purchase.rate_b}, C={purchase.rate_c}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Error converting rates for {product.product_name}: {e}")
                                purchase.rate_a = 0.0
                                purchase.rate_b = 0.0
                                purchase.rate_c = 0.0
                            
                            # Calculate actual rate - only paid quantity for billing
                            if purchase.purchase_calculation_mode == 'flat':
                                total_amount_calc = float(purchase_rate) * float(quantity)  # Only paid quantity
                                if float(discount) > total_amount_calc:
                                    errors.append(f"Row {i+1}: Flat discount cannot exceed total amount for {product.product_name}")
                                    continue
                                purchase.actual_rate_per_qty = float(purchase_rate) - (float(discount) / float(quantity)) if float(quantity) > 0 else float(purchase_rate)
                            else:
                                if float(discount) > 100.0:
                                    errors.append(f"Row {i+1}: Percentage discount cannot exceed 100% for {product.product_name}")
                                    continue
                                purchase.actual_rate_per_qty = float(purchase_rate) * (1 - (float(discount) / 100.0))
                            
                            purchase.product_actual_rate = purchase.actual_rate_per_qty
                            
                            # Calculate base amount before tax - only paid quantity for billing
                            base_amount = purchase.product_actual_rate * quantity  # Only paid quantity
                            
                            # Calculate tax amounts
                            cgst_amount = base_amount * (cgst / 100)
                            sgst_amount = base_amount * (sgst / 100)
                            
                            # Total amount including taxes - only for paid quantity
                            purchase.total_amount = base_amount + cgst_amount + sgst_amount
                            purchase.product_transportation_charges = 0  # Will be calculated later
                            
                            total_amount += purchase.total_amount
                            logger.info(f"Product {product.product_name}: Base={base_amount}, CGST={cgst_amount}, SGST={sgst_amount}, Total={purchase.total_amount}")
                            purchase.save()
                            print(f"DEBUG: Purchase saved successfully with ID: {purchase.purchaseid}")
                            print(f"DEBUG: Checking saved value - free_qty in DB: {purchase.product_free_qty}")
                            products_added += 1
                            logger.info(f"Product {product.product_name} added to invoice")
                            
                            logger.info(f"PURCHASE CREATED: {product.product_name}, Batch: {batch_no}, Qty: {quantity}, Free Qty: {free_qty}")
                            
                            # Save sale rates if provided
                            rate_A = product_data.get('rate_a') or product_data.get('rate_A')
                            rate_B = product_data.get('rate_b') or product_data.get('rate_B')
                            rate_C = product_data.get('rate_c') or product_data.get('rate_C')
                            
                            if rate_A or rate_B or rate_C:
                                try:
                                    SaleRateMaster.objects.update_or_create(
                                        productid=product,
                                        product_batch_no=batch_no,
                                        defaults={
                                            'rate_A': float(str(rate_A)) if rate_A else 0,
                                            'rate_B': float(str(rate_B)) if rate_B else 0,
                                            'rate_C': float(str(rate_C)) if rate_C else 0
                                        }
                                    )
                                except (ValueError, TypeError):
                                    logger.warning(f"Invalid sale rates for {product.product_name}, skipping rate setup")
                            
                        except ProductMaster.DoesNotExist:
                            errors.append(f"Row {i+1}: Product with ID {product_data['productid']} not found")
                            continue
                        except Exception as e:
                            import traceback
                            error_trace = traceback.format_exc()
                            errors.append(f"Row {i+1}: Error processing product: {str(e)}")
                            logger.error(f"Error processing product {i+1}: {e}")
                            logger.error(f"Full traceback: {error_trace}")
                            continue
                
                # Allow invoice creation even without products
                if products_added == 0:
                    logger.info(f"Invoice {invoice.invoice_no} created without products - header only")
                    if errors:
                        # Show errors as warnings but don't prevent invoice creation
                        for error in errors[:3]:  # Show first 3 errors
                            messages.warning(request, error)
                    messages.info(request, "📄 Invoice created without products. You can add products later by editing the invoice.")
                
                # Don't distribute transport charges - keep separate
                transport_charges_val = float(str(invoice.transport_charges)) if invoice.transport_charges else 0.0
                
                # Invoice total = products total + transport charges
                invoice.invoice_total = total_amount + transport_charges_val
                invoice.save()
                logger.info(f"Products total: {total_amount}, Transport: {transport_charges_val}, Invoice total: {invoice.invoice_total}")
                
                # Move challan entries to SupplierChallanMaster2 if pulled from challan
                if is_from_challan or is_mixed_mode:
                    moved_count = 0
                    for product_data in products:
                        challan_no = product_data.get('challan_no', '')
                        if challan_no and str(challan_no).strip():
                            try:
                                # Find matching challan entries
                                challan_entries = SupplierChallanMaster.objects.filter(
                                    product_challan_no=str(challan_no).strip(),
                                    product_id=product_data.get('productid'),
                                    product_batch_no=product_data.get('batch_no', '').strip()
                                )
                                
                                for entry in challan_entries:
                                    # Copy to SupplierChallanMaster2
                                    SupplierChallanMaster2.objects.create(
                                        product_suppliername=entry.product_suppliername,
                                        product_challan_id=entry.product_challan_id,
                                        product_challan_no=entry.product_challan_no,
                                        product_id=entry.product_id,
                                        product_name=entry.product_name,
                                        product_company=entry.product_company,
                                        product_packing=entry.product_packing,
                                        product_batch_no=entry.product_batch_no,
                                        product_expiry=entry.product_expiry,
                                        product_mrp=entry.product_mrp,
                                        product_purchase_rate=entry.product_purchase_rate,
                                        product_quantity=entry.product_quantity,
                                        product_free_qty=entry.product_free_qty,
                                        product_scheme=entry.product_scheme,
                                        product_discount=entry.product_discount,
                                        product_transportation_charges=entry.product_transportation_charges,
                                        actual_rate_per_qty=entry.actual_rate_per_qty,
                                        product_actual_rate=entry.product_actual_rate,
                                        total_amount=entry.total_amount,
                                        challan_entry_date=entry.challan_entry_date,
                                        cgst=entry.cgst,
                                        sgst=entry.sgst,
                                        challan_calculation_mode=entry.challan_calculation_mode,
                                        rate_a=entry.rate_a,
                                        rate_b=entry.rate_b,
                                        rate_c=entry.rate_c
                                    )
                                    # Delete from SupplierChallanMaster
                                    entry.delete()
                                    moved_count += 1
                                    logger.info(f"Moved challan entry to SupplierChallanMaster2: {entry.product_name} - {entry.product_batch_no}")
                            except Exception as e:
                                logger.error(f"Error moving challan entry: {e}")
                    
                    if moved_count > 0:
                        logger.info(f"Total {moved_count} challan entries moved to SupplierChallanMaster2")
                
                # Show any non-critical errors as warnings
                if errors:
                    for error in errors[:3]:  # Show first 3 errors
                        messages.warning(request, error)
                
                # Success message based on whether products were added
                if products_added > 0:
                    success_msg = f"Purchase Invoice #{invoice.invoice_no} with {products_added} products added successfully!"
                else:
                    success_msg = f"Purchase Invoice #{invoice.invoice_no} created successfully (header only)!"
                
                messages.success(request, success_msg)
                logger.info(f"Invoice {invoice.invoice_no} created successfully with {products_added} products")
                return redirect('invoice_detail', pk=invoice.invoiceid)
                
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"Unexpected error creating invoice: {e}")
            logger.error(f"Full error traceback: {error_trace}")
            messages.error(request, f"Error creating invoice: {str(e)}")
            print(f"\n\n=== INVOICE CREATION ERROR ===")
            print(f"Error: {e}")
            print(f"Traceback:\n{error_trace}")
            print(f"=== END ERROR ===")
            # Return to form
            suppliers = SupplierMaster.objects.all().order_by('supplier_name')
            products = ProductMaster.objects.all().order_by('product_name')
            context = {
                'invoice_form': InvoiceForm(),
                'suppliers': suppliers,
                'products': products,
                'title': 'Add Invoice with Products'
            }
            return render(request, 'purchases/combined_invoice_form.html', context)
    else:
        # GET request - show the form
        invoice_form = InvoiceForm()
    
    # Get suppliers and products for dropdowns
    suppliers = SupplierMaster.objects.all().order_by('supplier_name')
    products = ProductMaster.objects.all().order_by('product_name')
    
    context = {
        'invoice_form': invoice_form,
        'suppliers': suppliers,
        'products': products,
        'title': 'Add Invoice with Products'
    }
    return render(request, 'purchases/combined_invoice_form.html', context)



@login_required
def get_existing_batches(request):
    """API endpoint to get batches from both Purchase and Supplier Challan entries"""
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Product ID required'})
        
        from .stock_manager import StockManager
        from .models import ReturnPurchaseMaster, ReturnSalesMaster, SupplierChallanMaster
        
        batches_dict = {}
        
        # 1. Get batches from PurchaseMaster
        purchase_batches = PurchaseMaster.objects.filter(productid=product_id).values(
            'product_batch_no', 'product_expiry', 'product_MRP', 'product_purchase_rate'
        ).distinct()
        
        for batch in purchase_batches:
            batch_no = batch['product_batch_no']
            try:
                batch_stock_info = StockManager._get_batch_stock(product_id, batch_no)
                current_stock = batch_stock_info['batch_stock']
            except Exception:
                total_purchased = PurchaseMaster.objects.filter(
                    productid=product_id, product_batch_no=batch_no
                ).aggregate(total=Sum('product_quantity'))['total'] or 0
                total_sold = SalesMaster.objects.filter(
                    productid=product_id, product_batch_no=batch_no
                ).aggregate(total=Sum('sale_quantity'))['total'] or 0
                purchase_returns = ReturnPurchaseMaster.objects.filter(
                    returnproductid=product_id, returnproduct_batch_no=batch_no
                ).aggregate(total=Sum('returnproduct_quantity'))['total'] or 0
                sales_returns = ReturnSalesMaster.objects.filter(
                    return_productid=product_id, return_product_batch_no=batch_no
                ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
                current_stock = total_purchased - total_sold - purchase_returns + sales_returns
            
            if current_stock >= 0:
                latest_purchase = PurchaseMaster.objects.filter(
                    productid=product_id, product_batch_no=batch_no
                ).select_related('product_invoiceid', 'product_supplierid').order_by('-purchase_entry_date').first()
                
                supplier_challan = None
                if latest_purchase:
                    try:
                        challan = SupplierChallanMaster.objects.filter(
                            product_id=product_id, product_batch_no=batch_no
                        ).select_related('product_challan_id').order_by('-challan_entry_date').first()
                        if challan:
                            supplier_challan = {
                                'challan_no': challan.product_challan_no,
                                'challan_date': challan.product_challan_id.challan_date.strftime('%d-%m-%Y')
                            }
                    except Exception:
                        pass
                
                batches_dict[batch_no] = {
                    'batch_no': batch_no,
                    'expiry': batch['product_expiry'],
                    'mrp': batch['product_MRP'],
                    'purchase_rate': latest_purchase.product_purchase_rate if latest_purchase else batch['product_purchase_rate'],
                    'stock': current_stock,
                    'supplier_name': latest_purchase.product_supplierid.supplier_name if latest_purchase else 'N/A',
                    'invoice_no': latest_purchase.product_invoice_no if latest_purchase else 'N/A',
                    'supplier_challan': supplier_challan
                }
        
        # 2. Get batches from SupplierChallanMaster
        challan_batches = SupplierChallanMaster.objects.filter(product_id=product_id).values(
            'product_batch_no', 'product_expiry', 'product_mrp', 'product_purchase_rate'
        ).distinct()
        
        for batch in challan_batches:
            batch_no = batch['product_batch_no']
            if batch_no in batches_dict:
                continue
            
            try:
                batch_stock_info = StockManager._get_batch_stock(product_id, batch_no)
                current_stock = batch_stock_info['batch_stock']
            except Exception:
                total_challan = SupplierChallanMaster.objects.filter(
                    product_id=product_id, product_batch_no=batch_no
                ).aggregate(total=Sum('product_quantity'))['total'] or 0
                total_sold = SalesMaster.objects.filter(
                    productid=product_id, product_batch_no=batch_no
                ).aggregate(total=Sum('sale_quantity'))['total'] or 0
                sales_returns = ReturnSalesMaster.objects.filter(
                    return_productid=product_id, return_product_batch_no=batch_no
                ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
                current_stock = total_challan - total_sold + sales_returns
            
            if current_stock >= 0:
                latest_challan = SupplierChallanMaster.objects.filter(
                    product_id=product_id, product_batch_no=batch_no
                ).select_related('product_challan_id', 'product_suppliername').order_by('-challan_entry_date').first()
                
                batches_dict[batch_no] = {
                    'batch_no': batch_no,
                    'expiry': batch['product_expiry'],
                    'mrp': batch['product_mrp'],
                    'purchase_rate': latest_challan.product_purchase_rate if latest_challan else batch['product_purchase_rate'],
                    'stock': current_stock,
                    'supplier_name': latest_challan.product_suppliername.supplier_name if latest_challan else 'N/A',
                    'invoice_no': 'N/A',
                    'supplier_challan': {
                        'challan_no': latest_challan.product_challan_no,
                        'challan_date': latest_challan.product_challan_id.challan_date.strftime('%d-%m-%Y')
                    } if latest_challan else None
                }
        
        return JsonResponse({'success': True, 'batches': list(batches_dict.values())})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})




@login_required
def cleanup_duplicate_batches(request):
    """Clean up duplicate SaleRateMaster entries to fix product list duplicates"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                from django.db.models import Count
                
                # Find all duplicate SaleRateMaster entries
                duplicates = SaleRateMaster.objects.values(
                    'productid', 'product_batch_no'
                ).annotate(
                    count=Count('id')
                ).filter(count__gt=1)
                
                cleaned_count = 0
                duplicate_groups = 0
                
                for duplicate in duplicates:
                    # Get all entries for this product-batch combination
                    entries = SaleRateMaster.objects.filter(
                        productid=duplicate['productid'],
                        product_batch_no=duplicate['product_batch_no']
                    ).order_by('id')
                    
                    if entries.count() > 1:
                        duplicate_groups += 1
                        # Keep the first entry, delete the rest
                        entries_to_delete = entries[1:]
                        
                        for entry in entries_to_delete:
                            entry.delete()
                            cleaned_count += 1
                
                return JsonResponse({
                    'success': True,
                    'message': f'Successfully cleaned up {cleaned_count} duplicate entries from {duplicate_groups} product-batch combinations',
                    'cleaned_count': cleaned_count,
                    'duplicate_groups': duplicate_groups
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error during cleanup: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method. Use POST.'
    })

@login_required
def get_batch_inventory_status(request):
    """Get current inventory status for a specific batch"""
    if request.method == 'GET':
        try:
            product_id = request.GET.get('product_id')
            batch_no = request.GET.get('batch_no')
            
            if not product_id or not batch_no:
                return JsonResponse({
                    'success': False,
                    'error': 'Product ID and Batch Number are required'
                })
            
            # Get current stock for this batch
            from django.db.models import Sum
            
            # Total purchased quantity
            total_purchased = PurchaseMaster.objects.filter(
                productid=product_id,
                product_batch_no=batch_no
            ).aggregate(total=Sum('product_quantity'))['total'] or 0
            
            # Check if SaleRateMaster entry exists
            sale_rate_count = SaleRateMaster.objects.filter(
                productid_id=product_id,
                product_batch_no=batch_no
            ).count()
            
            return JsonResponse({
                'success': True,
                'product_id': product_id,
                'batch_no': batch_no,
                'total_stock': total_purchased,
                'sale_rate_entries': sale_rate_count,
                'has_duplicates': sale_rate_count > 1
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def cleanup_product_duplicates(request):
    """Clean up duplicate entries for a specific product"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            batch_no = data.get('batch_no')
            
            if not product_id or not batch_no:
                return JsonResponse({
                    'success': False,
                    'error': 'Product ID and Batch Number are required'
                })
            
            with transaction.atomic():
                # Clean SaleRateMaster duplicates for this specific batch
                sale_rate_entries = SaleRateMaster.objects.filter(
                    productid_id=product_id,
                    product_batch_no=batch_no
                ).order_by('id')
                
                cleaned_count = 0
                if sale_rate_entries.count() > 1:
                    # Keep first entry, delete rest
                    entries_to_delete = sale_rate_entries[1:]
                    for entry in entries_to_delete:
                        entry.delete()
                        cleaned_count += 1
                
                return JsonResponse({
                    'success': True,
                    'message': f'Cleaned {cleaned_count} duplicate entries for batch {batch_no}',
                    'cleaned_count': cleaned_count
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

@login_required
def get_supplier_challans(request):
    """API endpoint to get challans for a specific supplier"""
    try:
        supplier_id = request.GET.get('supplier_id')
        if not supplier_id:
            return JsonResponse({'success': False, 'error': 'Supplier ID required'})
        
        # Get challans that have entries in SupplierChallanMaster (not yet moved to SupplierChallanMaster2)
        # This ensures that once all products from a challan are invoiced and moved to SupplierChallanMaster2,
        # the challan won't appear in the Pull Challan list anymore
        challan_ids_with_entries = SupplierChallanMaster.objects.filter(
            product_suppliername_id=supplier_id
        ).values_list('product_challan_id', flat=True).distinct()
        
        challans = Challan1.objects.filter(
            challan_id__in=challan_ids_with_entries,
            supplier_id=supplier_id
        ).order_by('-challan_date', '-challan_id')
        
        challan_data = []
        for challan in challans:
            challan_data.append({
                'challan_id': challan.challan_id,
                'challan_no': challan.challan_no,
                'challan_date': challan.challan_date.isoformat(),
                'challan_total': float(challan.challan_total),
                'challan_paid': float(challan.challan_paid),
                'supplier_name': challan.supplier.supplier_name
            })
        
        return JsonResponse({
            'success': True,
            'challans': challan_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching supplier challans: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@login_required
def get_challan_products(request):
    """API endpoint to get products from selected challans"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        challan_ids = data.get('challan_ids', [])
        
        if not challan_ids:
            return JsonResponse({'success': False, 'error': 'No challan IDs provided'})
        
        # Get all products from the selected challans (only from SupplierChallanMaster, not SupplierChallanMaster2)
        # This ensures that once products are moved to SupplierChallanMaster2, they won't appear in Pull Challan list
        challan_products = SupplierChallanMaster.objects.filter(
            product_challan_id__in=challan_ids
        ).select_related('product_id', 'product_suppliername')
        
        products_data = []
        for product in challan_products:
            # Get sale rates - first try from challan, then from SaleRateMaster
            rate_a = float(product.rate_a) if hasattr(product, 'rate_a') and product.rate_a else 0.0
            rate_b = float(product.rate_b) if hasattr(product, 'rate_b') and product.rate_b else 0.0
            rate_c = float(product.rate_c) if hasattr(product, 'rate_c') and product.rate_c else 0.0
            
            # If rates not in challan, try SaleRateMaster
            if rate_a == 0.0 and rate_b == 0.0 and rate_c == 0.0:
                try:
                    sale_rates = SaleRateMaster.objects.get(
                        productid=product.product_id,
                        product_batch_no=product.product_batch_no
                    )
                    rate_a = float(sale_rates.rate_A) if sale_rates.rate_A else 0.0
                    rate_b = float(sale_rates.rate_B) if sale_rates.rate_B else 0.0
                    rate_c = float(sale_rates.rate_C) if sale_rates.rate_C else 0.0
                except SaleRateMaster.DoesNotExist:
                    pass
            
            # Get challan date
            challan_date_str = ''
            if product.product_challan_id:
                try:
                    challan_date_str = product.product_challan_id.challan_date.strftime('%d-%m-%Y')
                except:
                    challan_date_str = ''
            
            products_data.append({
                'product_id': product.product_id.productid,
                'product_name': product.product_name or '',
                'product_company': product.product_company or '',
                'product_packing': product.product_packing or '',
                'product_batch_no': product.product_batch_no or '',
                'product_expiry': product.product_expiry or '',
                'product_mrp': float(product.product_mrp) if product.product_mrp else 0.0,
                'product_purchase_rate': float(product.product_purchase_rate) if product.product_purchase_rate else 0.0,
                'product_quantity': float(product.product_quantity) if product.product_quantity else 0.0,
                'product_free_qty': float(product.product_free_qty) if hasattr(product, 'product_free_qty') and product.product_free_qty else 0.0,
                'product_discount': float(product.product_discount) if product.product_discount else 0.0,
                'cgst': float(product.cgst) if product.cgst else 2.5,
                'sgst': float(product.sgst) if product.sgst else 2.5,
                'rate_a': rate_a,
                'rate_b': rate_b,
                'rate_c': rate_c,
                'challan_no': product.product_challan_no or '',
                'challan_date': challan_date_str
            })
        
        return JsonResponse({
            'success': True,
            'products': products_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching challan products: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })