from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.utils import timezone
from .models import (
    StockIssueMaster, StockIssueDetail, ProductMaster, Web_User
)
import json

@login_required
def stock_issue_list(request):
    """Display list of stock issues"""
    issues = StockIssueMaster.objects.all().order_by('-issue_date', '-issue_id')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        issues = issues.filter(
            Q(issue_no__icontains=search_query) |
            Q(issue_type__icontains=search_query) |
            Q(remarks__icontains=search_query)
        )
    
    # Filter by issue type
    issue_type_filter = request.GET.get('issue_type', '')
    if issue_type_filter:
        issues = issues.filter(issue_type=issue_type_filter)
    
    # Pagination
    paginator = Paginator(issues, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'issue_type_filter': issue_type_filter,
        'issue_types': StockIssueMaster.ISSUE_TYPES,
    }
    
    return render(request, 'stock_issues/stock_issue_list.html', context)

@login_required
def add_stock_issue(request):
    """Add new stock issue"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create stock issue master
                issue = StockIssueMaster.objects.create(
                    issue_type=request.POST.get('issue_type'),
                    issue_date=request.POST.get('issue_date'),
                    remarks=request.POST.get('remarks', ''),
                    created_by=request.user
                )
                # Save to generate issue_no
                issue.save()
                
                # Process issue details
                products_data = json.loads(request.POST.get('products_data', '[]'))
                total_value = 0
                
                for item in products_data:
                    if item.get('product_id') and item.get('quantity_issued'):
                        product = ProductMaster.objects.get(productid=item['product_id'])
                        quantity_issued = float(item['quantity_issued'])
                        unit_rate = float(item.get('unit_rate', 0))

                        # Validate stock availability using transaction-based calculation
                        from .utils import get_batch_stock_status
                        current_stock, current_free_qty, is_available = get_batch_stock_status(product.productid, item['batch_no'])
                        if current_stock < quantity_issued:
                            raise ValueError(f"Insufficient stock for {product.product_name} - Batch {item['batch_no']}. Available: {current_stock}, Required: {quantity_issued}")

                        # Create stock issue detail
                        detail = StockIssueDetail.objects.create(
                            issue=issue,
                            product=product,
                            batch_no=item['batch_no'],
                            expiry_date=item['expiry_date'],
                            quantity_issued=quantity_issued,
                            unit_rate=unit_rate,
                            remarks=item.get('remarks', '')
                        )
                        total_value += detail.total_amount
                
                # Update total value
                issue.total_value = total_value
                issue.save()
                
                messages.success(request, f'Stock Issue {issue.issue_no} created successfully!')
                return redirect('stock_issue_detail', pk=issue.issue_id)
                
        except Exception as e:
            messages.error(request, f'Error creating stock issue: {str(e)}')
    
    # Get all products for client-side search
    products = ProductMaster.objects.all().order_by('product_name')
    
    context = {
        'issue_types': StockIssueMaster.ISSUE_TYPES,
        'today': timezone.now().date(),
        'products': products,
    }
    
    return render(request, 'stock_issues/stock_issue_form.html', context)

@login_required
def stock_issue_detail(request, pk):
    """Display stock issue details"""
    issue = get_object_or_404(StockIssueMaster, issue_id=pk)
    details = issue.details.all().order_by('detail_id')
    
    context = {
        'issue': issue,
        'details': details,
    }
    
    return render(request, 'stock_issues/stock_issue_detail.html', context)

@login_required
def delete_stock_issue(request, pk):
    """Delete stock issue"""
    issue = get_object_or_404(StockIssueMaster, issue_id=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                issue_no = issue.issue_no
                issue.delete()
                messages.success(request, f'Stock Issue {issue_no} deleted successfully!')
                return redirect('stock_issue_list')
        except Exception as e:
            messages.error(request, f'Error deleting stock issue: {str(e)}')
    
    return render(request, 'stock_issues/stock_issue_confirm_delete.html', {'issue': issue})

@login_required
def get_product_batch_info(request):
    """API endpoint to get product batch information for stock issue - uses same logic as sales form"""
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'error': 'Product ID required'}, status=400)
    
    try:
        from .utils import get_batch_stock_status
        from .models import PurchaseMaster, SupplierChallanMaster, SaleRateMaster, ProductMaster
        
        product = ProductMaster.objects.get(productid=product_id)
        
        # Get all unique batches from both purchases and supplier challans (same as sales form)
        purchase_batches = PurchaseMaster.objects.filter(
            productid=product
        ).values(
            'product_batch_no',
            'product_expiry', 
            'product_MRP',
            'product_actual_rate'
        ).distinct()
        
        challan_batches = SupplierChallanMaster.objects.filter(
            product_id=product
        ).values(
            'product_batch_no',
            'product_expiry', 
            'product_mrp',
            'product_purchase_rate'
        ).distinct()
        
        # Combine batches from both sources
        all_batches = {}
        for batch in purchase_batches:
            key = batch['product_batch_no']
            all_batches[key] = {
                'product_batch_no': batch['product_batch_no'],
                'product_expiry': batch['product_expiry'],
                'product_MRP': batch['product_MRP'],
                'product_actual_rate': batch['product_actual_rate']
            }
        
        for batch in challan_batches:
            key = batch['product_batch_no']
            if key not in all_batches:
                all_batches[key] = {
                    'product_batch_no': batch['product_batch_no'],
                    'product_expiry': batch['product_expiry'],
                    'product_MRP': batch['product_mrp'],
                    'product_actual_rate': batch['product_purchase_rate']
                }
        
        batches = list(all_batches.values())
        
        # Convert expiry date to MM-YYYY format (same as sales form)
        def convert_expiry_to_mmyyyy(expiry_input):
            if not expiry_input:
                return ''
            
            expiry_str = str(expiry_input).strip()
            
            # Handle YYYY-MM-DD format (convert to MM-YYYY)
            if len(expiry_str) == 10 and expiry_str.count('-') == 2:
                parts = expiry_str.split('-')
                if len(parts) == 3 and len(parts[0]) == 4:
                    return f"{parts[1]}-{parts[0]}"
            
            # Handle MM-YYYY format (already correct)
            if len(expiry_str) == 7 and expiry_str.count('-') == 1:
                parts = expiry_str.split('-')
                if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 4:
                    return expiry_str
            
            # Handle MMYY format (convert to MM-YYYY)
            if len(expiry_str) == 4 and expiry_str.isdigit():
                month = expiry_str[:2]
                year = '20' + expiry_str[2:4]
                return f"{month}-{year}"
            
            return expiry_str
        
        batch_list = []
        for batch in batches:
            batch_no = batch['product_batch_no']
            
            # Use the same stock calculation function as sales form
            current_stock, current_free_qty, is_available = get_batch_stock_status(product_id, batch_no)
            
            print(f"🔍 Stock Issue API - Product {product_id}, Batch {batch_no}: Stock = {current_stock}, Available = {is_available}")
            
            # Only include batches with stock > 0
            if current_stock > 0:
                # Convert expiry to MM-YYYY format
                expiry_mmyyyy = convert_expiry_to_mmyyyy(batch['product_expiry'])
                
                batch_list.append({
                    'batch_no': batch_no,
                    'expiry': expiry_mmyyyy,
                    'stock': current_stock,
                    'mrp': float(batch['product_MRP'] or 0),
                    'purchase_rate': float(batch['product_actual_rate'] or batch['product_MRP'] or 0),
                    'is_available': True
                })
        
        # Sort by expiry date (earliest first)
        batch_list.sort(key=lambda x: x['expiry'] if x['expiry'] else '9999-12')
        
        return JsonResponse({
            'success': True,
            'batches': batch_list
        })
        
    except ProductMaster.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Product with ID {product_id} not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def search_products_for_issue(request):
    """API endpoint to search products for stock issue"""
    originalSearchTerm = request.GET.get('q', '').strip()
    searchTerm = originalSearchTerm.lower()
    
    # Special case for loading all products
    if originalSearchTerm in ['*', 'all'] or len(originalSearchTerm) < 1:
        try:
            # Get all products
            products = ProductMaster.objects.all()[:200]  # Limit for performance
            
            filtered_products = []
            for product in products:
                filtered_products.append({
                    'id': product.productid,
                    'name': product.product_name,
                    'company': product.product_company,
                    'packing': product.product_packing or '',
                    'barcode': product.product_barcode or '',
                })
            
            return JsonResponse({'products': filtered_products})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    if len(originalSearchTerm) < 2:
        return JsonResponse({'products': []})
    
    try:
        # Get all products
        products = ProductMaster.objects.all()
        
        # Filter products that contain the search term
        filtered_products = []
        
        for product in products:
            # Check if search term matches
            name_contains = searchTerm in product.product_name.lower()
            company_contains = searchTerm in product.product_company.lower()
            barcode_matches = product.product_barcode and searchTerm in product.product_barcode.lower()
            
            if name_contains or company_contains or barcode_matches:
                # Priority scoring for better matches
                score = 0
                
                # Exact case "starts with" gets highest priority (1000 points)
                if product.product_name.startswith(originalSearchTerm):
                    score += 1000
                elif product.product_company.startswith(originalSearchTerm):
                    score += 900
                # Case-insensitive "starts with" gets high priority (500 points)
                elif product.product_name.lower().startswith(searchTerm):
                    score += 500
                elif product.product_company.lower().startswith(searchTerm):
                    score += 400
                # Contains gets much lower priority (10 points)
                elif name_contains:
                    score += 10
                elif company_contains:
                    score += 5
                elif barcode_matches:
                    score += 1
                
                filtered_products.append({
                    'id': product.productid,
                    'name': product.product_name,
                    'company': product.product_company,
                    'packing': product.product_packing or '',
                    'barcode': product.product_barcode or '',
                    'score': score
                })
        
        # Sort by score (higher score first), then alphabetically
        filtered_products.sort(key=lambda x: (-x['score'], x['name']))
        
        # Remove score from final result and limit to 20
        final_products = []
        for product in filtered_products[:20]:
            del product['score']
            final_products.append(product)
        
        return JsonResponse({'products': final_products})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)