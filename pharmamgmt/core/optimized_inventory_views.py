"""
Optimized Inventory Views
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from .models import ProductMaster, PurchaseMaster, SalesMaster, SaleRateMaster, Pharmacy_Details


@login_required
def inventory_list(request):
    """Fast inventory list using cache"""
    from .models import ProductInventoryCache, BatchInventoryCache
    from django.views.decorators.cache import never_cache
    
    # Disable browser cache
    request.META['HTTP_CACHE_CONTROL'] = 'no-cache'
    
    search_query = request.GET.get('search', '').strip()
    offset = int(request.GET.get('offset', 0))
    limit = 50
    
    products = ProductMaster.objects.all()
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_company__icontains=search_query) |
            Q(product_salt__icontains=search_query)
        )
    
    total_count = products.count()
    products = products.order_by('product_name')[offset:offset + limit]
    
    inventory_data = []
    for product in products:
        try:
            cache = ProductInventoryCache.objects.get(product_id=product.productid)
            current_stock = cache.total_stock
            stock_value = cache.total_stock_value
            status = cache.stock_status
        except ProductInventoryCache.DoesNotExist:
            current_stock = 0
            stock_value = 0
            status = 'out_of_stock'
        
        batches_info = []
        batch_caches = BatchInventoryCache.objects.filter(
            product_id=product.productid,
            current_stock__gt=0
        ).order_by('-current_stock')
        
        for batch_cache in batch_caches:
            batches_info.append({
                'batch_no': batch_cache.batch_no,
                'expiry': batch_cache.expiry_date,
                'mrp': batch_cache.mrp,
                'stock': batch_cache.total_stock,
                'rates': type('obj', (object,), {
                    'rate_A': batch_cache.rate_a,
                    'rate_B': batch_cache.rate_b,
                    'rate_C': batch_cache.rate_c
                })
            })
        
        inventory_data.append({
            'product': product,
            'current_stock': current_stock,
            'stock_value': stock_value,
            'status': status,
            'batches_info': batches_info
        })
    
    page_total_value = sum(item['stock_value'] for item in inventory_data)
    page_low_stock = sum(1 for item in inventory_data if 0 < item['current_stock'] <= 10)
    page_out_of_stock = sum(1 for item in inventory_data if item['current_stock'] <= 0)
    
    import time
    context = {
        'inventory_data': inventory_data,
        'search_query': search_query,
        'total_products': total_count,
        'page_total_value': page_total_value,
        'page_low_stock': page_low_stock,
        'page_out_of_stock': page_out_of_stock,
        'pharmacy': Pharmacy_Details.objects.first(),
        'has_more': offset + limit < total_count,
        'next_offset': offset + limit,
        'title': 'All Products Inventory',
        'cache_buster': int(time.time())
    }
    
    response = render(request, 'inventory/inventory_list.html', context)
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response
