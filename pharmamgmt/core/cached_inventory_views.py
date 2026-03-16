"""
Cached Inventory Views - Using ProductInventoryCache and BatchInventoryCache
Super fast inventory display using pre-calculated cache tables
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from .models import ProductInventoryCache, BatchInventoryCache, ProductMaster


@login_required
def inventory_list_cached(request):
    """
    Show ALL products (with and without stock) - cache on-the-fly
    """
    from .inventory_cache import update_all_batches_for_product
    
    search_query = request.GET.get('search', '').strip()
    offset = int(request.GET.get('offset', 0))
    
    # Get ALL products but optimize with prefetch
    products = ProductMaster.objects.prefetch_related(
        'inventory_cache', 'batch_caches'
    ).all()
    
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_company__icontains=search_query) |
            Q(product_category__icontains=search_query)
        )
    
    products = products.order_by('product_name')
    
    # Manual pagination with offset
    per_page = 25  # Smaller pages for faster loading
    start = offset
    end = offset + per_page
    
    products_slice = products[start:end]
    total_count = products.count()
    has_more = end < total_count
    next_offset = end if has_more else None
    
    # Prepare data with on-the-fly cache
    inventory_data = []
    for product in products_slice:
        # Use prefetched cache (no additional queries)
        cache = getattr(product, 'inventory_cache', None)
        
        # Use prefetched batches (no additional queries)
        batches = [b for b in product.batch_caches.all() if b.current_stock > 0]
        
        batches_info = [{
            'batch_no': b.batch_no,
            'expiry': b.expiry_date,
            'stock': b.total_stock,
            'mrp': b.mrp,
            'purchase_rate': b.purchase_rate,
            'rates': {'rate_A': b.rate_a, 'rate_B': b.rate_b, 'rate_C': b.rate_c}
        } for b in batches]
        
        inventory_data.append({
            'product': product,
            'total_stock': cache.total_stock if cache else 0,
            'total_batches': len(batches_info),
            'stock_value': cache.total_stock_value if cache else 0,
            'status': cache.stock_status if cache else 'out_of_stock',
            'batches_info': batches_info
        })
    
    # Statistics
    page_total_value = sum(item['stock_value'] for item in inventory_data)
    page_low_stock = sum(1 for item in inventory_data if item['status'] == 'low_stock')
    page_out_of_stock = sum(1 for item in inventory_data if item['status'] == 'out_of_stock')
    
    # Check if AJAX request for Load More
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        from django.template.loader import render_to_string
        
        html = render_to_string('inventory/inventory_rows.html', {'inventory_data': inventory_data})
        
        return JsonResponse({
            'success': True,
            'html': html,
            'has_more': has_more,
            'next_offset': next_offset,
            'total_count': total_count,
            'batch_stats': {
                'total_value': page_total_value,
                'low_stock': page_low_stock,
                'out_of_stock': page_out_of_stock
            }
        })
    
    context = {
        'inventory_data': inventory_data,
        'search_query': search_query,
        'total_products': total_count,
        'page_total_value': page_total_value,
        'page_low_stock': page_low_stock,
        'page_out_of_stock': page_out_of_stock,
        'has_more': has_more,
        'next_offset': next_offset,
    }
    
    return render(request, 'inventory/inventory_list.html', context)
