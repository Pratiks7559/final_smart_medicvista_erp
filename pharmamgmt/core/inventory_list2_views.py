from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Count, Max
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from .models import (
    InventoryTransaction, ProductMaster, Pharmacy_Details, SaleRateMaster,
    PurchaseMaster, SalesMaster, ReturnPurchaseMaster,
    ReturnSalesMaster, SupplierChallanMaster, CustomerChallanMaster,
    StockIssueDetail,
)
from decimal import Decimal


def _date_range_filters(start_date, end_date):
    filters = {}
    if start_date:
        filters['__gte'] = start_date
    if end_date:
        filters['__lte'] = end_date
    return filters


def _filter_inventory_transactions_by_source_date(queryset, start_date=None, end_date=None):
    """Filter movements by the date on their originating business document."""
    if not start_date and not end_date:
        return queryset

    date_filters = _date_range_filters(start_date, end_date)
    source_ids = (
        ('PURCHASE', PurchaseMaster.objects.filter(
            **{f'product_invoiceid__invoice_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('purchaseid')),
        ('SALE', SalesMaster.objects.filter(
            **{f'sales_invoice_no__sales_invoice_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('id')),
        ('PURCHASE_RETURN', ReturnPurchaseMaster.objects.filter(
            **{f'returninvoiceid__returninvoice_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('returnpurchaseid')),
        ('SALES_RETURN', ReturnSalesMaster.objects.filter(
            **{f'return_sales_invoice_no__return_sales_invoice_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('return_sales_id')),
        ('SUPPLIER_CHALLAN', SupplierChallanMaster.objects.filter(
            **{f'product_challan_id__challan_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('challan_id')),
        ('CUSTOMER_CHALLAN', CustomerChallanMaster.objects.filter(
            **{f'customer_challan_id__customer_challan_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('customer_challan_master_id')),
        ('STOCK_ISSUE', StockIssueDetail.objects.filter(
            **{f'issue__issue_date{suffix}': value for suffix, value in date_filters.items()},
        ).values('detail_id')),
    )

    source_filter = Q(pk__in=[])
    for transaction_type, reference_ids in source_ids:
        source_filter |= Q(transaction_type=transaction_type, reference_id__in=reference_ids)
    return queryset.filter(source_filter)


def _get_inventory_transaction_source_dates(transactions):
    transactions_by_type = {}
    for transaction in transactions:
        transactions_by_type.setdefault(transaction.transaction_type, set()).add(transaction.reference_id)

    date_maps = {
        'PURCHASE': dict(PurchaseMaster.objects.filter(
            purchaseid__in=transactions_by_type.get('PURCHASE', set())
        ).values_list('purchaseid', 'product_invoiceid__invoice_date')),
        'SALE': dict(SalesMaster.objects.filter(
            id__in=transactions_by_type.get('SALE', set())
        ).values_list('id', 'sales_invoice_no__sales_invoice_date')),
        'PURCHASE_RETURN': dict(ReturnPurchaseMaster.objects.filter(
            returnpurchaseid__in=transactions_by_type.get('PURCHASE_RETURN', set())
        ).values_list('returnpurchaseid', 'returninvoiceid__returninvoice_date')),
        'SALES_RETURN': dict(ReturnSalesMaster.objects.filter(
            return_sales_id__in=transactions_by_type.get('SALES_RETURN', set())
        ).values_list('return_sales_id', 'return_sales_invoice_no__return_sales_invoice_date')),
        'SUPPLIER_CHALLAN': dict(SupplierChallanMaster.objects.filter(
            challan_id__in=transactions_by_type.get('SUPPLIER_CHALLAN', set())
        ).values_list('challan_id', 'product_challan_id__challan_date')),
        'CUSTOMER_CHALLAN': dict(CustomerChallanMaster.objects.filter(
            customer_challan_master_id__in=transactions_by_type.get('CUSTOMER_CHALLAN', set())
        ).values_list('customer_challan_master_id', 'customer_challan_id__customer_challan_date')),
        'STOCK_ISSUE': dict(StockIssueDetail.objects.filter(
            detail_id__in=transactions_by_type.get('STOCK_ISSUE', set())
        ).values_list('detail_id', 'issue__issue_date')),
    }
    return {
        transaction.transaction_id: date_maps.get(transaction.transaction_type, {}).get(
            transaction.reference_id,
            transaction.transaction_date.date(),
        )
        for transaction in transactions
    }


def _build_inventory2_data(search_query='', stock_filter='all', start_date=None, end_date=None):
    transactions = _filter_inventory_transactions_by_source_date(
        InventoryTransaction.objects.all(), start_date, end_date
    )
    stock_summary = transactions.values(
        'product_id',
        'product__product_name',
        'product__product_company',
        'product__product_packing',
        'product__product_salt',
        'product__product_category',
    ).annotate(
        total_stock=Sum('quantity'),
        total_free=Sum('free_quantity'),
        batch_count=Count('batch_no', distinct=True),
    ).order_by('product__product_name')

    if search_query:
        stock_summary = stock_summary.filter(
            Q(product__product_name__icontains=search_query)
            | Q(product__product_company__icontains=search_query)
            | Q(product__product_salt__icontains=search_query)
            | Q(product__product_category__icontains=search_query)
        )

    stock_data = list(stock_summary)
    product_ids = [item['product_id'] for item in stock_data]
    products = ProductMaster.objects.in_bulk(product_ids)
    all_batches = transactions.filter(product_id__in=product_ids).values(
        'product_id', 'batch_no'
    ).annotate(
        stock=Sum('quantity'),
        free_stock=Sum('free_quantity'),
        mrp=Max('mrp'),
        expiry_date=Max('expiry_date'),
    ).order_by('product_id', 'expiry_date', 'batch_no')
    batches_by_product = {}
    for batch in all_batches:
        batches_by_product.setdefault(batch['product_id'], []).append(batch)

    product_rates = SaleRateMaster.objects.filter(
        productid_id__in=product_ids
    ).values('productid_id', 'product_batch_no', 'rate_A', 'rate_B', 'rate_C')
    rates_lookup = {
        (rate['productid_id'], rate['product_batch_no']): {
            'rate_A': rate['rate_A'],
            'rate_B': rate['rate_B'],
            'rate_C': rate['rate_C'],
        }
        for rate in product_rates
    }

    inventory_data = []
    for item in stock_data:
        product_id = item['product_id']
        batches_info = []
        total_stock = 0
        stock_value = 0

        for batch in batches_by_product.get(product_id, []):
            quantity = batch['stock'] or 0
            free_quantity = batch['free_stock'] or 0
            batch_stock = quantity + free_quantity
            total_stock += batch_stock
            stock_value += quantity * (batch['mrp'] or 0)
            batches_info.append({
                'batch_no': batch['batch_no'],
                'expiry': batch['expiry_date'],
                'stock': batch_stock,
                'qty': quantity,
                'free_qty': free_quantity,
                'mrp': batch['mrp'] or 0,
                'rates': rates_lookup.get(
                    (product_id, batch['batch_no']),
                    {'rate_A': 0, 'rate_B': 0, 'rate_C': 0},
                ),
            })

        if start_date or end_date:
            if total_stock < 0:
                status = 'Net Outflow'
            elif total_stock == 0:
                status = 'No Net Movement'
            elif total_stock < 10:
                status = 'Low Net Inflow'
            else:
                status = 'Net Inflow'
        elif total_stock <= 0:
            status = 'Out of Stock'
        elif total_stock < 10:
            status = 'Low Stock'
        else:
            status = 'In Stock'

        if stock_filter == 'in_stock' and total_stock < 10:
            continue
        if stock_filter == 'low_stock' and not 0 < total_stock < 10:
            continue
        if stock_filter == 'out_of_stock' and total_stock > 0:
            continue

        inventory_data.append({
            'product': products[product_id],
            'product_name': item['product__product_name'],
            'company': item['product__product_company'],
            'packing': item['product__product_packing'],
            'category': item['product__product_category'] or 'N/A',
            'total_stock': total_stock,
            'stock_value': stock_value,
            'batch_count': item['batch_count'],
            'status': status,
            'batches_info': batches_info,
        })
    return inventory_data


@login_required
def inventory_list2(request):
    """
    Optimized Inventory list using InventoryTransaction system
    Real-time accurate stock with optimized queries
    """
    
    # Get filter parameters
    search_query = request.GET.get('search', '').strip()
    stock_filter = request.GET.get('stock_filter', 'all')
    from .inventory_date_filters import get_inventory_date_range
    start_date, end_date, valid_range = get_inventory_date_range(
        request, start_param='start_date', end_param='end_date'
    )
    inventory_data = _build_inventory2_data(
        search_query,
        stock_filter,
        start_date,
        end_date,
    ) if valid_range else []
    
    # Manual pagination
    offset = int(request.GET.get('offset', 0))
    per_page = 50
    start = offset
    end = offset + per_page
    
    inventory_slice = inventory_data[start:end]
    total_count = len(inventory_data)
    has_more = end < total_count
    next_offset = end if has_more else None
    
    # Page statistics
    total_value = sum(item['stock_value'] for item in inventory_data)
    total_low_stock = sum(1 for item in inventory_data if item['status'] == 'Low Stock')
    total_out_of_stock = sum(1 for item in inventory_data if item['status'] == 'Out of Stock')
    
    # Check if AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        from django.template.loader import render_to_string
        
        html = render_to_string('inventory/inventory_rows.html', {
            'inventory_data': inventory_slice,
            'start_date': start_date,
            'end_date': end_date,
        })
        
        return JsonResponse({
            'success': True,
            'html': html,
            'has_more': has_more,
            'next_offset': next_offset,
            'total_count': total_count,
        })
    
    context = {
        'inventory_data': inventory_slice,
        'search_query': search_query,
        'stock_filter': stock_filter,
        'start_date': start_date,
        'end_date': end_date,
        'period_filtered': bool(start_date or end_date),
        'total_products': total_count,
        'page_total_value': total_value,
        'page_low_stock': total_low_stock,
        'page_out_of_stock': total_out_of_stock,
        'has_more': has_more,
        'next_offset': next_offset,
        'pharmacy': Pharmacy_Details.objects.first(),
        'title': 'Inventory List 2 (Real-time)',
    }
    
    return render(request, 'inventory/inventory_list2.html', context)


@login_required
def inventory_batches(request, product_id):
    """
    Get batch details for a product (AJAX endpoint)
    """
    from django.http import JsonResponse
    
    batches = InventoryTransaction.objects.filter(
        product_id=product_id
    ).values(
        'batch_no', 'expiry_date', 'mrp'
    ).annotate(
        total_qty=Sum('quantity'),
        total_free_qty=Sum('free_quantity'),
        last_rate=Max('rate')
    ).filter(
        Q(total_qty__gt=0) | Q(total_free_qty__gt=0)
    ).order_by('expiry_date', 'batch_no')
    
    batch_list = []
    for batch in batches:
        batch_list.append({
            'batch_no': batch['batch_no'],
            'expiry_date': batch['expiry_date'],
            'mrp': float(batch['mrp']),
            'stock': float(batch['total_qty'] or 0),
            'free_stock': float(batch['total_free_qty'] or 0),
            'total_stock': float((batch['total_qty'] or 0) + (batch['total_free_qty'] or 0)),
            'last_rate': float(batch['last_rate'] or 0)
        })
    
    return JsonResponse({'batches': batch_list})


@login_required
def inventory_transaction_history(request, product_id):
    """View transaction history for a product with pagination"""

    product = get_object_or_404(ProductMaster, productid=product_id)
    batch_no = request.GET.get('batch_no', '')
    from .inventory_date_filters import get_inventory_date_range
    start_date, end_date, valid_range = get_inventory_date_range(
        request, start_param='start_date', end_param='end_date'
    )

    transactions = InventoryTransaction.objects.filter(product=product)
    if batch_no:
        transactions = transactions.filter(batch_no=batch_no)
    if valid_range:
        transactions = _filter_inventory_transactions_by_source_date(
            transactions, start_date, end_date
        )
    else:
        transactions = transactions.none()

    all_transactions = list(transactions.select_related('created_by'))
    source_dates = _get_inventory_transaction_source_dates(all_transactions)
    all_transactions.sort(
        key=lambda txn: (source_dates[txn.transaction_id], txn.transaction_id)
    )
    balance_lookup = {}
    running_balance = Decimal('0')
    for txn in all_transactions:
        running_balance += Decimal(str(txn.quantity)) + Decimal(str(txn.free_quantity))
        balance_lookup[txn.transaction_id] = running_balance

    # Display newest source-document dates first while retaining chronological balances.
    display_transactions = list(reversed(all_transactions))
    paginator = Paginator(display_transactions, 15)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    transaction_list = [{
        'transaction': txn,
        'transaction_display_date': source_dates[txn.transaction_id],
        'balance': balance_lookup[txn.transaction_id],
    } for txn in page_obj]

    query_params = request.GET.copy()
    query_params.pop('page', None)
    context = {
        'product': product,
        'batch_no': batch_no,
        'transactions': transaction_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'start_date': start_date,
        'end_date': end_date,
        'query_without_page': query_params.urlencode(),
        'title': f'Transaction History - {product.product_name}'
    }
    
    return render(request, 'inventory/transaction_history.html', context)


@login_required
def inventory_dashboard(request):
    """Dashboard with inventory statistics"""
    
    # Get summary statistics using optimized queries
    stats = InventoryTransaction.objects.aggregate(
        total_stock=Sum('quantity'),
        total_free=Sum('free_quantity'),
        total_transactions=Count('transaction_id')
    )
    
    # Get products with stock
    products_with_stock = InventoryTransaction.objects.values('product_id').annotate(
        total=Sum('quantity') + Sum('free_quantity')
    ).filter(total__gt=0).count()
    
    # Get low stock products
    low_stock_products = InventoryTransaction.objects.values('product_id').annotate(
        total=Sum('quantity') + Sum('free_quantity')
    ).filter(total__lte=10, total__gt=0).count()
    
    # Get out of stock products
    all_products = ProductMaster.objects.count()
    out_of_stock = all_products - products_with_stock
    
    context = {
        'total_stock': stats['total_stock'] or 0,
        'total_free': stats['total_free'] or 0,
        'total_transactions': stats['total_transactions'],
        'products_with_stock': products_with_stock,
        'low_stock_products': low_stock_products,
        'out_of_stock_products': out_of_stock,
        'title': 'Inventory Dashboard'
    }
    
    return render(request, 'inventory/dashboard.html', context)



@login_required
def export_inventory2_pdf(request):
    """Export inventory list 2 to PDF"""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    import io
    from datetime import datetime
    
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=0.5*inch)
        
        styles = getSampleStyleSheet()
        story = []
        
        search_query = request.GET.get('search', '').strip()
        stock_filter = request.GET.get('stock_filter', 'all')
        from .inventory_date_filters import get_inventory_date_range
        start_date, end_date, valid_range = get_inventory_date_range(
            request, start_param='start_date', end_param='end_date'
        )
        if not valid_range:
            return HttpResponse('Invalid date range.', status=400)
        inventory_data = _build_inventory2_data(
            search_query, stock_filter, start_date, end_date
        )
        total_value = sum(item['stock_value'] for item in inventory_data)
        
        # Pharmacy header
        try:
            pharmacy = Pharmacy_Details.objects.first()
            if pharmacy:
                title_style = styles['Heading1']
                title_style.alignment = 1
                if pharmacy.pharmaname:
                    story.append(Paragraph(pharmacy.pharmaname.upper(), title_style))
                info_style = styles['Normal']
                info_style.alignment = 1
                info_style.fontSize = 9
                pharmacy_info = []
                if pharmacy.proprietorcontact:
                    pharmacy_info.append(f"Contact: {pharmacy.proprietorcontact}")
                if pharmacy.proprietoremail:
                    pharmacy_info.append(f"Email: {pharmacy.proprietoremail}")
                if pharmacy_info:
                    story.append(Paragraph(" | ".join(pharmacy_info), info_style))
                story.append(Spacer(1, 0.15*inch))
        except:
            pass
        
        # Title
        title_style = styles['Heading1']
        title_style.alignment = 1
        title = Paragraph("ALL PRODUCTS INVENTORY MOVEMENT REPORT", title_style)
        story.append(title)
        period_text = (
            f"Movement period: {start_date or 'No lower bound'} to {end_date or 'No upper bound'}"
            if start_date or end_date else 'All available transaction dates'
        )
        story.append(Paragraph(period_text, styles['Normal']))
        
        # Date
        date_style = styles['Normal']
        date_style.alignment = 1
        date_text = Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}", date_style)
        story.append(date_text)
        story.append(Spacer(1, 0.3*inch))
        
        # Summary
        total_products = len(inventory_data)
        out_of_stock = sum(1 for item in inventory_data if item['total_stock'] <= 0)
        low_stock = sum(1 for item in inventory_data if 0 < item['total_stock'] < 10)
        
        summary_data = [
            ['Total Products', 'Net Movement Value', 'Net Outflow/Zero', 'Low Net Inflow'],
            [str(total_products), f"₹{total_value:,.2f}", str(out_of_stock), str(low_stock)]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2.5*inch, 1.5*inch, 1.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Inventory table
        table_data = [['Product Name', 'Company', 'Packing', 'Category', 'Batches', 'Net Stock', 'Net Value']]
        
        for item in inventory_data:
            table_data.append([
                item['product_name'][:25] + '...' if len(item['product_name']) > 25 else item['product_name'],
                item['company'][:15] + '...' if len(item['company']) > 15 else item['company'],
                item['packing'][:10] + '...' if len(item['packing']) > 10 else item['packing'],
                item['category'][:10] + '...' if len(item['category']) > 10 else item['category'],
                str(item['batch_count']),
                str(item['total_stock']),
                f"₹{item['stock_value']:.2f}"
            ])
        
        inventory_table = Table(table_data, repeatRows=1)
        inventory_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONT', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 1), (6, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        
        story.append(inventory_table)
        
        doc.build(story)
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="inventory_report_realtime.pdf"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def export_inventory2_excel(request):
    """Export inventory list 2 to Excel"""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from datetime import datetime
    import io
    
    try:
        search_query = request.GET.get('search', '').strip()
        stock_filter = request.GET.get('stock_filter', 'all')
        from .inventory_date_filters import get_inventory_date_range
        start_date, end_date, valid_range = get_inventory_date_range(
            request, start_param='start_date', end_param='end_date'
        )
        if not valid_range:
            return HttpResponse('Invalid date range.', status=400)
        inventory_data = _build_inventory2_data(
            search_query, stock_filter, start_date, end_date
        )
        total_value = sum(item['stock_value'] for item in inventory_data)
        
        # Create workbook
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventory Report"
        
        # Styles
        header_font = Font(bold=True, size=12, color="FFFFFF")
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Pharmacy header
        try:
            pharmacy = Pharmacy_Details.objects.first()
            if pharmacy:
                ws['A1'] = pharmacy.pharmaname or "Pharmacy"
                ws['A1'].font = Font(bold=True, size=14)
                ws['A1'].alignment = Alignment(horizontal='center')
                ws.merge_cells('A1:G1')
                
                ws['A2'] = f"Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}"
                ws['A2'].alignment = Alignment(horizontal='center')
                ws.merge_cells('A2:G2')
                
                current_row = 4
            else:
                current_row = 1
        except:
            current_row = 1
        
        # Title
        ws[f'A{current_row}'] = "ALL PRODUCTS INVENTORY MOVEMENT REPORT"
        ws[f'A{current_row}'].font = Font(bold=True, size=14)
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        ws.merge_cells(f'A{current_row}:G{current_row}')
        current_row += 2

        period_text = (
            f"Movement period: {start_date or 'No lower bound'} to {end_date or 'No upper bound'}"
            if start_date or end_date else 'All available transaction dates'
        )
        ws[f'A{current_row}'] = period_text
        ws.merge_cells(f'A{current_row}:G{current_row}')
        current_row += 2
        
        # Summary
        ws[f'A{current_row}'] = "Total Products"
        ws[f'B{current_row}'] = len(inventory_data)
        ws[f'C{current_row}'] = "Net Movement Value"
        ws[f'D{current_row}'] = f"₹{total_value:,.2f}"
        current_row += 2
        
        # Headers
        headers = ['Product Name', 'Company', 'Packing', 'Category', 'Batches', 'Net Stock', 'Net Value']
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col_num)
            cell.value = header
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border
        
        current_row += 1
        
        # Data rows
        for item in inventory_data:
            ws.cell(row=current_row, column=1, value=item['product_name']).border = border
            ws.cell(row=current_row, column=2, value=item['company']).border = border
            ws.cell(row=current_row, column=3, value=item['packing']).border = border
            ws.cell(row=current_row, column=4, value=item['category']).border = border
            ws.cell(row=current_row, column=5, value=item['batch_count']).border = border
            ws.cell(row=current_row, column=6, value=float(item['total_stock'])).border = border
            ws.cell(row=current_row, column=7, value=float(item['stock_value'])).border = border
            current_row += 1
        
        # Adjust column widths
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 20
        ws.column_dimensions['C'].width = 15
        ws.column_dimensions['D'].width = 15
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 12
        ws.column_dimensions['G'].width = 15
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="inventory_report_realtime.xlsx"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)
