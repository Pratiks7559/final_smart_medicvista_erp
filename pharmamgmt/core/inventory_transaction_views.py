"""
Test view to demonstrate InventoryTransaction usage
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from .models import InventoryTransaction, ProductMaster
from decimal import Decimal


@login_required
def inventory_transaction_test(request):
    """Test view to show inventory from InventoryTransaction table"""
    
    search_query = request.GET.get('search', '').strip()
    
    # Get products
    products = ProductMaster.objects.all()
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) |
            Q(product_company__icontains=search_query)
        )
    
    products = products[:50]  # Limit to 50 for testing
    
    inventory_data = []
    
    for product in products:
        # Get batch-wise stock using InventoryTransaction
        batches = InventoryTransaction.objects.filter(
            product=product
        ).values(
            'batch_no', 'expiry_date', 'mrp'
        ).annotate(
            total_qty=Sum('quantity'),
            total_free_qty=Sum('free_quantity'),
            last_rate=Sum('rate') / Count('rate')  # Average rate
        ).filter(
            Q(total_qty__gt=0) | Q(total_free_qty__gt=0)
        ).order_by('expiry_date', 'batch_no')
        
        # Calculate total stock
        total_stock = sum(b['total_qty'] or 0 for b in batches)
        total_free = sum(b['total_free_qty'] or 0 for b in batches)
        
        if total_stock > 0 or total_free > 0:
            inventory_data.append({
                'product': product,
                'total_stock': total_stock,
                'total_free': total_free,
                'batches': list(batches)
            })
    
    context = {
        'inventory_data': inventory_data,
        'search_query': search_query,
        'total_products': len(inventory_data)
    }
    
    return render(request, 'inventory/inventory_transaction_test.html', context)
