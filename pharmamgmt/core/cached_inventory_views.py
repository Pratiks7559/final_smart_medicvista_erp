"""
Cached Inventory Views - Using ProductInventoryCache and BatchInventoryCache
Super fast inventory display using pre-calculated cache tables
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count, Max
from .models import ProductInventoryCache, BatchInventoryCache, ProductMaster, InventoryTransaction, SaleRateMaster, Pharmacy_Details, InvoiceMaster, PurchaseMaster
from .year_filter_utils import get_financial_year_dates, get_current_financial_year


@login_required
def inventory_list_cached(request):
    """
    Show products with stock filtered by selected Financial Year
    """
    search_query = request.GET.get('search', '').strip()
    offset = int(request.GET.get('offset', 0))

    # Financial Year filter via Purchase Invoice date
    selected_year = request.session.get('selected_year', get_current_financial_year())
    fy_start, fy_end = get_financial_year_dates(selected_year)
    fy_label = f'{selected_year}-{str(selected_year + 1)[2:]}'

    # Get invoice IDs in selected FY
    fy_invoice_ids = list(
        InvoiceMaster.objects.filter(
            invoice_date__gte=fy_start,
            invoice_date__lte=fy_end
        ).values_list('invoiceid', flat=True)
    )

    # Get product_ids from PurchaseMaster whose invoice is in selected FY
    # Also include products that came via supplier challan in this FY
    from .models import SupplierChallanMaster
    purchase_pids = set(
        PurchaseMaster.objects.filter(
            product_invoiceid__in=fy_invoice_ids
        ).values_list('productid_id', flat=True)
    )
    challan_pids = set(
        SupplierChallanMaster.objects.filter(
            product_challan_id__challan_date__gte=fy_start,
            product_challan_id__challan_date__lte=fy_end
        ).values_list('product_id_id', flat=True)
    )
    fy_product_ids = list(purchase_pids | challan_pids)

    # Get stock summary from InventoryTransaction - only FY products, all transactions (cumulative stock)
    stock_qs = InventoryTransaction.objects.filter(
        product_id__in=fy_product_ids
    ).values('product_id').annotate(
        total_stock=Sum('quantity'),
        total_free=Sum('free_quantity')
    )

    if search_query:
        stock_qs = stock_qs.filter(
            Q(product__product_name__icontains=search_query) |
            Q(product__product_company__icontains=search_query) |
            Q(product__product_category__icontains=search_query)
        )

    stock_data = list(stock_qs)
    product_ids = [item['product_id'] for item in stock_data]

    # Manual pagination
    per_page = 25
    start = offset
    end = offset + per_page
    paginated_ids = product_ids[start:end]
    total_count = len(product_ids)
    has_more = end < total_count
    next_offset = end if has_more else None

    # Fetch products for this page
    products = ProductMaster.objects.filter(productid__in=paginated_ids)
    products_map = {p.productid: p for p in products}

    # Fetch ALL batches for this page's products (no FY filter)
    all_batches = InventoryTransaction.objects.filter(
        product_id__in=paginated_ids
    ).values('product_id', 'batch_no', 'expiry_date', 'mrp').annotate(
        stock=Sum('quantity'),
        free_stock=Sum('free_quantity')
    ).order_by('product_id', 'expiry_date', 'batch_no')

    # Fetch rates
    all_rates = SaleRateMaster.objects.filter(
        productid_id__in=paginated_ids
    ).values('productid_id', 'product_batch_no', 'rate_A', 'rate_B', 'rate_C')
    rates_lookup = {f"{r['productid_id']}_{r['product_batch_no']}": r for r in all_rates}

    batches_by_product = {}
    for batch in all_batches:
        pid = batch['product_id']
        batches_by_product.setdefault(pid, []).append(batch)

    inventory_data = []
    for pid in paginated_ids:
        product = products_map.get(pid)
        if not product:
            continue
        batches = batches_by_product.get(pid, [])
        total_stock = 0
        stock_value = 0
        batches_info = []
        for batch in batches:
            batch_stock = float(batch['stock'] or 0) + float(batch['free_stock'] or 0)
            total_stock += batch_stock
            stock_value += float(batch['stock'] or 0) * float(batch['mrp'] or 0)
            rate_key = f"{pid}_{batch['batch_no']}"
            rates = rates_lookup.get(rate_key, {'rate_A': 0, 'rate_B': 0, 'rate_C': 0})
            batches_info.append({
                'batch_no': batch['batch_no'],
                'expiry': batch['expiry_date'],
                'stock': batch_stock,
                'mrp': batch['mrp'] or 0,
                'rates': {'rate_A': rates.get('rate_A', 0), 'rate_B': rates.get('rate_B', 0), 'rate_C': rates.get('rate_C', 0)}
            })

        if total_stock <= 0:
            status = 'out_of_stock'
        elif total_stock < 10:
            status = 'low_stock'
        else:
            status = 'in_stock'

        inventory_data.append({
            'product': product,
            'total_stock': total_stock,
            'stock_value': stock_value,
            'status': status,
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
        'selected_year': selected_year,
        'fy_label': fy_label,
        'pharmacy': Pharmacy_Details.objects.first(),
    }

    return render(request, 'inventory/inventory_list.html', context)
