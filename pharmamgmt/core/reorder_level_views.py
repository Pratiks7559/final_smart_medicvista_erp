from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from .models import ProductMaster, SalesMaster, BatchInventoryCache, Pharmacy_Details
from core.year_filter_utils import apply_year_filter

@login_required
def reorder_level_report(request):
    """Display product-wise and batch-wise reorder levels with pagination"""
    
    # Get filter parameters
    product_search = request.GET.get('product_search', '')
    show_reorder_only = request.GET.get('show_reorder_only') == 'true'
    page_number = request.GET.get('page', 1)
    
    # Get all products with their batch inventory - optimized query
    products_query = ProductMaster.objects.select_related().prefetch_related(
        'batch_caches'
    ).all()
    
    if product_search:
        products_query = products_query.filter(
            Q(product_name__icontains=product_search) |
            Q(product_company__icontains=product_search)
        )
    
    reorder_data = []
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # Batch process to reduce memory usage
    for product in products_query:
        # Get all batches for this product - already prefetched
        batches = product.batch_caches.filter(current_stock__gt=0).order_by('expiry_date', 'batch_no')
        
        if not batches.exists():
            continue
        
        # Calculate total sales for this product (last 30 days)
        sales_qty = SalesMaster.objects.filter(
            productid=product,
            sale_entry_date__gte=thirty_days_ago
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        # Calculate reorder level: sale * 1.5
        avg_monthly_sale = float(sales_qty)
        reorder_level_qty = avg_monthly_sale * 1.5
        
        # Get total available stock for this product (excluding free qty)
        total_available = sum(float(batch.current_stock) for batch in batches)
        
        # Calculate reorder needed
        reorder_needed = max(0, reorder_level_qty - total_available)
        
        # Only include products that need reordering if filter is active
        if show_reorder_only and reorder_needed <= 0:
            continue
        
        # Build batch-wise data - minimal info for performance
        batch_details = []
        for batch in batches:
            batch_stock = float(batch.current_stock)  # Only current stock, no free qty
            batch_details.append({
                'batch_no': batch.batch_no,
                'expiry_date': batch.expiry_date,
                'mrp': batch.mrp,
                'purchase_rate': batch.purchase_rate,
                'available_stock': batch_stock,
                'free_qty': float(batch.current_free_qty),  # Show separately
                'rate_a': batch.rate_a,
                'rate_b': batch.rate_b,
                'rate_c': batch.rate_c,
            })
        
        reorder_data.append({
            'product_id': product.productid,
            'product_name': product.product_name,
            'product_company': product.product_company,
            'product_packing': product.product_packing,
            'avg_monthly_sale': avg_monthly_sale,
            'reorder_level': reorder_level_qty,
            'total_available': total_available,
            'reorder_needed': reorder_needed,
            'batches': batch_details,
            'status': 'critical' if reorder_needed > 0 else 'sufficient'
        })
    
    # Sort by reorder_needed (descending)
    reorder_data.sort(key=lambda x: x['reorder_needed'], reverse=True)
    
    # Add pagination - 20 items per page for better performance
    paginator = Paginator(reorder_data, 20)
    page_obj = paginator.get_page(page_number)
    
    # Get pharmacy details
    pharmacy = Pharmacy_Details.objects.first()
    
    context = {
        'title': 'Reorder Level Report',
        'page_obj': page_obj,
        'product_search': product_search,
        'show_reorder_only': show_reorder_only,
        'pharmacy': pharmacy,
        'total_products': len(reorder_data),
    }
    
    return render(request, 'purchases/reorder_level_report.html', context)


@login_required
def export_reorder_level_excel(request):
    """Export reorder level report as Excel"""
    
    # Get filter parameters
    product_search = request.GET.get('product_search', '')
    show_reorder_only = request.GET.get('show_reorder_only') == 'true'
    
    # Get all products
    products_query = ProductMaster.objects.all()
    
    if product_search:
        products_query = products_query.filter(
            Q(product_name__icontains=product_search) |
            Q(product_company__icontains=product_search)
        )
    
    data = []
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    for product in products_query:
        # Get all batches
        batches = BatchInventoryCache.objects.filter(
            product=product,
            current_stock__gt=0
        ).order_by('expiry_date', 'batch_no')
        
        if not batches.exists():
            continue
        
        # Calculate sales
        sales_qty = SalesMaster.objects.filter(
            productid=product,
            sale_entry_date__gte=thirty_days_ago
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        avg_monthly_sale = float(sales_qty)
        reorder_level_qty = avg_monthly_sale * 1.5
        total_available = sum(float(batch.current_stock) for batch in batches)  # Excluding free qty
        reorder_needed = max(0, reorder_level_qty - total_available)
        
        # Only include if reorder is needed
        if show_reorder_only and reorder_needed <= 0:
            continue
        
        # Add batch-wise rows
        for batch in batches:
            batch_stock = float(batch.current_stock)  # Only current stock
            free_qty = float(batch.current_free_qty)  # Free qty separately
            data.append({
                'Product Name': product.product_name,
                'Company': product.product_company,
                'Packing': product.product_packing,
                'Batch No': batch.batch_no,
                'Expiry': batch.expiry_date,
                'MRP': batch.mrp,
                'Purchase Rate': batch.purchase_rate,
                'Batch Stock': batch_stock,
                'Free Qty': free_qty,
                'Total Available': total_available,
                'Avg Monthly Sale': avg_monthly_sale,
                'Reorder Level (1.5x)': reorder_level_qty,
                'Reorder Needed': reorder_needed,
                'Rate A': batch.rate_a,
                'Rate B': batch.rate_b,
                'Rate C': batch.rate_c,
            })
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Create Excel response
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="reorder_level_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    
    # Write to Excel
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reorder Level', index=False, startrow=3)
        
        workbook = writer.book
        worksheet = writer.sheets['Reorder Level']
        
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter
        
        pharmacy = Pharmacy_Details.objects.first()
        
        # Add header
        if pharmacy:
            worksheet['A1'] = pharmacy.pharmaname.upper()
            worksheet['A1'].font = Font(size=16, bold=True)
            worksheet['A1'].alignment = Alignment(horizontal='center')
            worksheet.merge_cells('A1:P1')
        
        worksheet['A2'] = f'REORDER LEVEL REPORT - {datetime.now().strftime("%d-%m-%Y")}'
        worksheet['A2'].font = Font(size=12, bold=True)
        worksheet['A2'].alignment = Alignment(horizontal='center')
        worksheet.merge_cells('A2:P2')
        
        # Style header row
        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True)
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        for col in range(1, 17):  # A to P columns
            cell = worksheet.cell(row=4, column=col)
            cell.fill = header_fill
            cell.font = header_font
            cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Auto-adjust column widths
        column_widths = [25, 20, 10, 15, 10, 10, 12, 12, 10, 12, 15, 15, 15, 10, 10, 10]
        for i, width in enumerate(column_widths, 1):
            worksheet.column_dimensions[get_column_letter(i)].width = width
    
    return response
