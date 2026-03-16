from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum
from datetime import datetime
import io
import csv

# PDF imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Excel imports
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from .models import Pharmacy_Details, ProductMaster, PurchaseMaster, SalesMaster, ReturnPurchaseMaster, ReturnSalesMaster, SupplierChallanMaster, CustomerChallanMaster, StockIssueDetail
from django.db.models import Q
from collections import defaultdict
import calendar

def get_batch_inventory_data(search_query=''):
    """Optimized batch inventory data fetching with bulk queries"""
    from django.db.models import Sum, F, Q, FloatField, ExpressionWrapper
    
    # Base query for products
    products = ProductMaster.objects.all()
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) | 
            Q(product_company__icontains=search_query)
        )
    
    # Get all product IDs
    product_ids = list(products.values_list('productid', flat=True))
    
    if not product_ids:
        return []
    
    # Bulk fetch all purchases with batch info
    purchases = PurchaseMaster.objects.filter(
        productid__in=product_ids
    ).values(
        'productid', 'product_batch_no', 'product_expiry', 'product_MRP', 'product_free_qty'
    ).annotate(
        purchased_qty=Sum('product_quantity'),
        free_qty_total=Sum('product_free_qty')
    )
    
    # Bulk fetch all sales
    sales = SalesMaster.objects.filter(
        productid__in=product_ids
    ).values('productid', 'product_batch_no').annotate(
        sold_qty=Sum('sale_quantity')
    )
    
    # Bulk fetch purchase returns
    purchase_returns = ReturnPurchaseMaster.objects.filter(
        returnproductid__in=product_ids
    ).values('returnproductid', 'returnproduct_batch_no').annotate(
        return_qty=Sum('returnproduct_quantity')
    )
    
    # Bulk fetch sales returns
    sales_returns = ReturnSalesMaster.objects.filter(
        return_productid__in=product_ids
    ).values('return_productid', 'return_product_batch_no').annotate(
        return_qty=Sum('return_sale_quantity')
    )
    
    # Bulk fetch supplier challans
    supplier_challans = SupplierChallanMaster.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'product_batch_no').annotate(
        challan_qty=Sum('product_quantity')
    )
    
    # Bulk fetch customer challans
    customer_challans = CustomerChallanMaster.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'product_batch_no').annotate(
        challan_qty=Sum('sale_quantity')
    )
    
    # Bulk fetch stock issues
    stock_issues = StockIssueDetail.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'batch_no').annotate(
        issue_qty=Sum('quantity_issued')
    )
    
    # Create lookup dictionaries
    sales_dict = {}
    for s in sales:
        key = (s['productid'], s['product_batch_no'])
        sales_dict[key] = s['sold_qty'] or 0
    
    pr_dict = {}
    for pr in purchase_returns:
        key = (pr['returnproductid'], pr['returnproduct_batch_no'])
        pr_dict[key] = pr['return_qty'] or 0
    
    sr_dict = {}
    for sr in sales_returns:
        key = (sr['return_productid'], sr['return_product_batch_no'])
        sr_dict[key] = sr['return_qty'] or 0
    
    sc_dict = {}
    for sc in supplier_challans:
        key = (sc['product_id'], sc['product_batch_no'])
        sc_dict[key] = sc['challan_qty'] or 0
    
    cc_dict = {}
    for cc in customer_challans:
        key = (cc['product_id'], cc['product_batch_no'])
        cc_dict[key] = cc['challan_qty'] or 0
    
    si_dict = {}
    for si in stock_issues:
        key = (si['product_id'], si['batch_no'])
        si_dict[key] = si['issue_qty'] or 0
    
    # Create product lookup
    product_dict = {p.productid: p for p in products}
    
    # Build inventory list
    inventory = []
    for purchase in purchases:
        product_id = purchase['productid']
        batch_no = purchase['product_batch_no']
        key = (product_id, batch_no)
        
        # Calculate stock
        purchased = purchase['purchased_qty'] or 0
        sold = sales_dict.get(key, 0)
        returned_purchase = pr_dict.get(key, 0)
        returned_sales = sr_dict.get(key, 0)
        supplier_challan = sc_dict.get(key, 0)
        customer_challan = cc_dict.get(key, 0)
        issued = si_dict.get(key, 0)
        
        stock = (purchased + returned_sales + supplier_challan) - (sold + returned_purchase + customer_challan + issued)
        
        # Only include if stock > 0
        if stock > 0:
            product = product_dict.get(product_id)
            if product:
                mrp = float(purchase['product_MRP'] or 0)
                free_qty = float(purchase['free_qty_total'] or 0)
                value = stock * mrp
                
                inventory.append({
                    'product_id': product_id,
                    'product_name': product.product_name,
                    'product_company': product.product_company,
                    'product_packing': product.product_packing,
                    'batch_no': batch_no,
                    'expiry': purchase['product_expiry'] or '',
                    'mrp': mrp,
                    'stock': stock,
                    'free_qty': free_qty,
                    'value': value
                })
    
    return inventory

def get_dateexpiry_inventory_data(search_query=''):
    """Optimized date-wise inventory data fetching with bulk queries"""
    from django.db.models import Sum, F, Q, FloatField, ExpressionWrapper
    from datetime import datetime, date
    from collections import defaultdict
    
    # Base query for products
    products = ProductMaster.objects.all()
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) | 
            Q(product_company__icontains=search_query)
        )
    
    # Get all product IDs
    product_ids = list(products.values_list('productid', flat=True))
    
    if not product_ids:
        return [], 0
    
    # Bulk fetch all purchases with batch info
    purchases = PurchaseMaster.objects.filter(
        productid__in=product_ids
    ).values(
        'productid', 'product_batch_no', 'product_expiry', 'product_MRP', 'product_purchase_rate', 'purchase_entry_date'
    ).annotate(
        purchased_qty=Sum('product_quantity')
    )
    
    # Bulk fetch all sales
    sales = SalesMaster.objects.filter(
        productid__in=product_ids
    ).values('productid', 'product_batch_no').annotate(
        sold_qty=Sum('sale_quantity')
    )
    
    # Bulk fetch purchase returns
    purchase_returns = ReturnPurchaseMaster.objects.filter(
        returnproductid__in=product_ids
    ).values('returnproductid', 'returnproduct_batch_no').annotate(
        return_qty=Sum('returnproduct_quantity')
    )
    
    # Bulk fetch sales returns
    sales_returns = ReturnSalesMaster.objects.filter(
        return_productid__in=product_ids
    ).values('return_productid', 'return_product_batch_no').annotate(
        return_qty=Sum('return_sale_quantity')
    )
    
    # Bulk fetch supplier challans
    supplier_challans = SupplierChallanMaster.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'product_batch_no').annotate(
        challan_qty=Sum('product_quantity')
    )
    
    # Bulk fetch customer challans
    customer_challans = CustomerChallanMaster.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'product_batch_no').annotate(
        challan_qty=Sum('sale_quantity')
    )
    
    # Bulk fetch stock issues
    stock_issues = StockIssueDetail.objects.filter(
        product_id__in=product_ids
    ).values('product_id', 'batch_no').annotate(
        issue_qty=Sum('quantity_issued')
    )
    
    # Create lookup dictionaries
    sales_dict = {}
    for s in sales:
        key = (s['productid'], s['product_batch_no'])
        sales_dict[key] = s['sold_qty'] or 0
    
    pr_dict = {}
    for pr in purchase_returns:
        key = (pr['returnproductid'], pr['returnproduct_batch_no'])
        pr_dict[key] = pr['return_qty'] or 0
    
    sr_dict = {}
    for sr in sales_returns:
        key = (sr['return_productid'], sr['return_product_batch_no'])
        sr_dict[key] = sr['return_qty'] or 0
    
    sc_dict = {}
    for sc in supplier_challans:
        key = (sc['product_id'], sc['product_batch_no'])
        sc_dict[key] = sc['challan_qty'] or 0
    
    cc_dict = {}
    for cc in customer_challans:
        key = (cc['product_id'], cc['product_batch_no'])
        cc_dict[key] = cc['challan_qty'] or 0
    
    si_dict = {}
    for si in stock_issues:
        key = (si['product_id'], si['batch_no'])
        si_dict[key] = si['issue_qty'] or 0
    
    # Create product lookup
    product_dict = {p.productid: p for p in products}
    
    # Group by entry date
    date_groups = defaultdict(list)
    total_value = 0
    
    for purchase in purchases:
        product_id = purchase['productid']
        batch_no = purchase['product_batch_no']
        key = (product_id, batch_no)
        
        # Calculate stock
        purchased = purchase['purchased_qty'] or 0
        sold = sales_dict.get(key, 0)
        returned_purchase = pr_dict.get(key, 0)
        returned_sales = sr_dict.get(key, 0)
        supplier_challan = sc_dict.get(key, 0)
        customer_challan = cc_dict.get(key, 0)
        issued = si_dict.get(key, 0)
        
        stock = (purchased + returned_sales + supplier_challan) - (sold + returned_purchase + customer_challan + issued)
        
        # Only include if stock > 0
        if stock > 0:
            product = product_dict.get(product_id)
            if product:
                mrp = float(purchase['product_MRP'] or 0)
                purchase_rate = float(purchase['product_purchase_rate'] or 0)
                value = stock * mrp
                total_value += value
                
                # Get entry date
                entry_date = purchase['purchase_entry_date']
                if isinstance(entry_date, datetime):
                    entry_date = entry_date.date()
                
                date_key = entry_date.strftime('%Y-%m-%d') if entry_date else 'Unknown'
                
                date_groups[date_key].append({
                    'product_name': product.product_name,
                    'product_company': product.product_company,
                    'batch_no': batch_no,
                    'expiry': purchase['product_expiry'] or '',
                    'purchase_rate': purchase_rate,
                    'mrp': mrp,
                    'stock': stock,
                    'value': value
                })
    
    # Convert to list format with expiry info
    expiry_data = []
    for date_key, products_list in sorted(date_groups.items(), reverse=True):
        group_value = sum(p['value'] for p in products_list)
        
        # Calculate days to expiry if available
        days_to_expiry = None
        try:
            entry_date_obj = datetime.strptime(date_key, '%Y-%m-%d').date()
            days_to_expiry = (entry_date_obj - date.today()).days
        except:
            pass
        
        expiry_data.append({
            'expiry_display': date_key,
            'total_value': group_value,
            'days_to_expiry': days_to_expiry,
            'products': products_list
        })
    
    return expiry_data, total_value


@login_required
def export_batch_inventory_pdf(request):
    """Export batch-wise inventory report as PDF (Ctrl+Q)"""
    try:
        # Get search query
        search_query = request.GET.get('search', '')
        
        # Get inventory data
        all_inventory_data = get_batch_inventory_data(search_query)
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(A4), 
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        story = []

        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None

        # Styles
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, alignment=TA_CENTER, textColor=colors.darkblue)
        info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, spaceAfter=4)
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=6)
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                story.append(Paragraph(f"{pharmacy.pharmaname}", title_style))
            if pharmacy.proprietorname:
                story.append(Paragraph(f"Proprietor: {pharmacy.proprietorname}", info_style))
            if pharmacy.proprietorcontact:
                story.append(Paragraph(f"Contact: {pharmacy.proprietorcontact}", info_style))
            if pharmacy.proprietoremail:
                story.append(Paragraph(f"Email: {pharmacy.proprietoremail}", info_style))
            if pharmacy.pharmaweburl:
                story.append(Paragraph(f"Website: {pharmacy.pharmaweburl}", info_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("Batch-wise Inventory Report", title_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}", date_style))
        
        if search_query:
            story.append(Paragraph(f"Search Filter: {search_query}", date_style))
        
        story.append(Spacer(1, 0.2*inch))

        # Summary Statistics
        total_products = len(all_inventory_data)
        total_stock = sum(item['stock'] for item in all_inventory_data)
        total_mrp = sum(item['mrp'] * item['stock'] for item in all_inventory_data)
        total_value = sum(item['value'] for item in all_inventory_data)
        
        summary_data = [
            ['Total Products', 'Total Stock Qty', 'Total MRP Value', 'Total Inventory Value'],
            [str(total_products), str(int(total_stock)), f"₹{total_mrp:,.2f}", f"₹{total_value:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2*inch, 2*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))

        # Inventory Table - Group by product
        if all_inventory_data:
            # Group batches by product
            from collections import defaultdict
            product_groups = defaultdict(list)
            for item in all_inventory_data:
                key = (item['product_name'], item['product_company'], item['product_packing'])
                product_groups[key].append(item)
            
            table_data = [['Product Name', 'Company', 'Packing', 'Batch No', 'Expiry', 'Stock Qty', 'Free Qty', 'MRP', 'Stock Value']]
            
            for (prod_name, prod_company, prod_packing), batches in sorted(product_groups.items()):
                for idx, item in enumerate(batches):
                    # Format expiry date
                    expiry_display = item.get('expiry', 'N/A')
                    if expiry_display and expiry_display != 'N/A':
                        try:
                            if len(expiry_display) == 7 and '-' in expiry_display:  # MM-YYYY format
                                expiry_display = expiry_display
                            elif len(expiry_display) == 10:  # YYYY-MM-DD format
                                parts = expiry_display.split('-')
                                if len(parts) == 3:
                                    expiry_display = f"{parts[1]}-{parts[0]}"
                        except:
                            pass
                    
                    # Show product details only in first row of group
                    if idx == 0:
                        table_data.append([
                            prod_name[:25] + '...' if len(prod_name) > 25 else prod_name,
                            prod_company[:15] + '...' if len(prod_company) > 15 else prod_company,
                            prod_packing[:10] + '...' if len(prod_packing) > 10 else prod_packing,
                            item['batch_no'][:10] + '...' if len(item['batch_no']) > 10 else item['batch_no'],
                            expiry_display,
                            str(int(item['stock'])),
                            str(int(item.get('free_qty', 0))),
                            f"₹{item['mrp']:.2f}",
                            f"₹{item['value']:.2f}"
                        ])
                    else:
                        # Empty cells for product details, only show batch info
                        table_data.append([
                            '',
                            '',
                            '',
                            item['batch_no'][:10] + '...' if len(item['batch_no']) > 10 else item['batch_no'],
                            expiry_display,
                            str(int(item['stock'])),
                            str(int(item.get('free_qty', 0))),
                            f"₹{item['mrp']:.2f}",
                            f"₹{item['value']:.2f}"
                        ])

            # Create table with proper column widths for landscape
            col_widths = [2*inch, 1.2*inch, 0.7*inch, 0.7*inch, 0.6*inch, 0.6*inch, 0.6*inch, 0.7*inch, 0.9*inch]
            inventory_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            inventory_table.setStyle(TableStyle([
                # Header style
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                
                # Data rows style
                ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 1), (4, -1), 'LEFT'),
                ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),
                ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.darkblue),
            ]))

            story.append(inventory_table)
        else:
            no_data_text = Paragraph("No inventory data found.", styles['Normal'])
            story.append(no_data_text)

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"batch_inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def export_batch_inventory_excel(request):
    """Export batch-wise inventory report as Excel (Ctrl+E)"""
    try:
        # Get search query
        search_query = request.GET.get('search', '')
        
        # Get inventory data
        all_inventory_data = get_batch_inventory_data(search_query)
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Batch Inventory Report"
        
        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None

        # Styles
        title_font = Font(name='Arial', size=14, bold=True, color='1F4E79')
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        data_font = Font(name='Arial', size=10)
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        summary_fill = PatternFill(start_color='E7F3FF', end_color='E7F3FF', fill_type='solid')
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title section
        info_font = Font(name='Arial', size=10)
        current_row = 1
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = pharmacy.pharmaname
                ws[f'A{current_row}'].font = title_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorname:
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"Proprietor: {pharmacy.proprietorname}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorcontact:
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"Contact: {pharmacy.proprietorcontact}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietoremail:
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"Email: {pharmacy.proprietoremail}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.pharmaweburl:
                ws.merge_cells(f'A{current_row}:H{current_row}')
                ws[f'A{current_row}'] = f"Website: {pharmacy.pharmaweburl}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            current_row += 1
        
        ws.merge_cells(f'A{current_row}:H{current_row}')
        ws[f'A{current_row}'] = "Batch-wise Inventory Report"
        ws[f'A{current_row}'].font = title_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        ws.merge_cells(f'A{current_row}:H{current_row}')
        ws[f'A{current_row}'] = f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}"
        ws[f'A{current_row}'].font = info_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        if search_query:
            ws.merge_cells(f'A{current_row}:H{current_row}')
            ws[f'A{current_row}'] = f"Search Filter: {search_query}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        
        current_row += 1  # Empty row

        # Summary section
        total_products = len(all_inventory_data)
        total_stock = sum(item['stock'] for item in all_inventory_data)
        total_mrp = sum(item['mrp'] * item['stock'] for item in all_inventory_data)
        total_value = sum(item['value'] for item in all_inventory_data)
        
        summary_headers = ['Total Products', 'Total Stock Qty', 'Total MRP Value', 'Total Inventory Value']
        summary_values = [total_products, int(total_stock), f"₹{total_mrp:,.2f}", f"₹{total_value:,.2f}"]
        
        # Summary headers
        for col, header in enumerate(summary_headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        # Summary values
        for col, value in enumerate(summary_values, 1):
            cell = ws.cell(row=current_row, column=col, value=value)
            cell.font = data_font
            cell.fill = summary_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 2  # Empty row
        
        # Data table headers
        headers = ['Product Name', 'Company', 'Packing', 'Batch No', 'Expiry', 'Stock Qty', 'Free Qty', 'MRP', 'Stock Value']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        # Data rows - Group by product
        from collections import defaultdict
        product_groups = defaultdict(list)
        for item in all_inventory_data:
            key = (item['product_name'], item['product_company'], item['product_packing'])
            product_groups[key].append(item)
        
        for (prod_name, prod_company, prod_packing), batches in sorted(product_groups.items()):
            for idx, item in enumerate(batches):
                # Format expiry date
                expiry_display = item.get('expiry', 'N/A')
                if expiry_display and expiry_display != 'N/A':
                    try:
                        if len(expiry_display) == 7 and '-' in expiry_display:  # MM-YYYY format
                            expiry_display = expiry_display
                        elif len(expiry_display) == 10:  # YYYY-MM-DD format
                            parts = expiry_display.split('-')
                            if len(parts) == 3:
                                expiry_display = f"{parts[1]}-{parts[0]}"
                    except:
                        pass
                
                # Show product details only in first row of group
                if idx == 0:
                    row_data = [
                        prod_name,
                        prod_company,
                        prod_packing,
                        item['batch_no'],
                        expiry_display,
                        int(item['stock']),
                        int(item.get('free_qty', 0)),
                        f"₹{item['mrp']:.2f}",
                        f"₹{item['value']:.2f}"
                    ]
                else:
                    # Empty cells for product details, only show batch info
                    row_data = [
                        '',
                        '',
                        '',
                        item['batch_no'],
                        expiry_display,
                        int(item['stock']),
                        int(item.get('free_qty', 0)),
                        f"₹{item['mrp']:.2f}",
                        f"₹{item['value']:.2f}"
                    ]
                
                for col, value in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col, value=value)
                    cell.font = data_font
                    cell.border = thin_border
                    
                    # Alignment
                    if col in [6, 7, 8, 9]:  # Numeric columns
                        cell.alignment = Alignment(horizontal='right')
                    else:
                        cell.alignment = Alignment(horizontal='left')
                    
                    # Highlight zero stock
                    if col == 6 and int(item['stock']) <= 0:
                        cell.font = Font(name='Arial', size=10, color='FF0000', bold=True)
                
                current_row += 1
        
        # Auto-adjust column widths
        column_widths = [30, 20, 15, 15, 12, 12, 12, 12, 15]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"batch_inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)


@login_required
def export_dateexpiry_inventory_pdf(request):
    """Export date-wise inventory report as PDF (Ctrl+Q)"""
    try:
        # Get search query and filters
        search_query = request.GET.get('search', '')
        expiry_from = request.GET.get('expiry_from', '')
        expiry_to = request.GET.get('expiry_to', '')
        
        # Get inventory data
        expiry_data, total_value = get_dateexpiry_inventory_data(search_query)
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=landscape(A4), 
            topMargin=0.5*inch, 
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        # Create styles
        styles = getSampleStyleSheet()
        story = []

        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None

        # Styles
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, alignment=TA_CENTER, textColor=colors.darkblue)
        info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, spaceAfter=4)
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=6)
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                story.append(Paragraph(f"{pharmacy.pharmaname}", title_style))
            if pharmacy.proprietorname:
                story.append(Paragraph(f"Proprietor: {pharmacy.proprietorname}", info_style))
            if pharmacy.proprietorcontact:
                story.append(Paragraph(f"Contact: {pharmacy.proprietorcontact}", info_style))
            if pharmacy.proprietoremail:
                story.append(Paragraph(f"Email: {pharmacy.proprietoremail}", info_style))
            if pharmacy.pharmaweburl:
                story.append(Paragraph(f"Website: {pharmacy.pharmaweburl}", info_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("Date-wise Inventory Report", title_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}", date_style))
        
        if expiry_from and expiry_to:
            story.append(Paragraph(f"Entry Date Filter: {expiry_from} to {expiry_to}", date_style))
        elif expiry_from:
            story.append(Paragraph(f"Entry Date From: {expiry_from}", date_style))
        elif expiry_to:
            story.append(Paragraph(f"Entry Date To: {expiry_to}", date_style))
        
        if search_query:
            story.append(Paragraph(f"Search Filter: {search_query}", date_style))
        
        story.append(Spacer(1, 0.2*inch))

        # Summary
        total_products = sum(len(group['products']) for group in expiry_data)
        
        summary_data = [
            ['Total Products', 'Total Inventory Value', 'Expiry Groups'],
            [str(total_products), f"₹{total_value:,.2f}", str(len(expiry_data))]
        ]
        
        summary_table = Table(summary_data, colWidths=[2*inch, 2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))

        # Expiry-wise data
        if expiry_data:
            for expiry_group in expiry_data:
                # Group header
                group_style = ParagraphStyle(
                    'GroupHeader',
                    parent=styles['Heading3'],
                    fontSize=12,
                    spaceAfter=6,
                    textColor=colors.darkgreen,
                    backColor=colors.lightgrey
                )
                
                expiry_display = expiry_group['expiry_display']
                group_value = expiry_group['total_value']
                days_info = ""
                
                if expiry_group.get('days_to_expiry') is not None:
                    days = expiry_group['days_to_expiry']
                    if days < 0:
                        days_info = f" (Expired {abs(days)} days ago)"
                    elif days == 0:
                        days_info = " (Expires today)"
                    else:
                        days_info = f" ({days} days remaining)"
                
                # Products table for this group - 4 columns matching HTML template
                table_data = [['Product Name', 'Purchase Rate', 'MRP', 'Stock Value']]
                
                for product in expiry_group['products']:
                    table_data.append([
                        product['product_name'][:40] + '...' if len(product['product_name']) > 40 else product['product_name'],
                        f"₹{product['purchase_rate']:.2f}",
                        f"₹{product['mrp']:.2f}",
                        f"₹{product['value']:.2f}"
                    ])
                
                # Create table with 4 columns
                col_widths = [4*inch, 1.5*inch, 1.5*inch, 1.5*inch]
                products_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                
                # Determine row color based on expiry status
                row_color = colors.white
                if expiry_group.get('days_to_expiry') is not None:
                    days = expiry_group['days_to_expiry']
                    if days < 0:
                        row_color = colors.mistyrose  # Expired
                    elif days <= 30:
                        row_color = colors.lightyellow  # Expiring soon
                    elif days <= 90:
                        row_color = colors.lightcyan  # Warning
                
                products_table.setStyle(TableStyle([
                    # Header style
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    
                    # Data rows style
                    ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
                    ('BACKGROUND', (0, 1), (-1, -1), row_color),
                    
                    # Grid
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ]))
                
                story.append(products_table)
                story.append(Spacer(1, 0.2*inch))
        else:
            no_data_text = Paragraph("No inventory data found.", styles['Normal'])
            story.append(no_data_text)

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"dateexpiry_inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def export_dateexpiry_inventory_excel(request):
    """Export date-wise inventory report as Excel (Ctrl+E)"""
    try:
        # Get search query and filters
        search_query = request.GET.get('search', '')
        expiry_from = request.GET.get('expiry_from', '')
        expiry_to = request.GET.get('expiry_to', '')
        
        # Get inventory data
        expiry_data, total_value = get_dateexpiry_inventory_data(search_query)
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "Date-wise Inventory Report"
        
        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None

        # Styles
        title_font = Font(name='Arial', size=14, bold=True, color='1F4E79')
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        group_font = Font(name='Arial', size=12, bold=True, color='2F5233')
        data_font = Font(name='Arial', size=10)
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        summary_fill = PatternFill(start_color='E7F3FF', end_color='E7F3FF', fill_type='solid')
        group_fill = PatternFill(start_color='E2EFDA', end_color='E2EFDA', fill_type='solid')
        expired_fill = PatternFill(start_color='FFE6E6', end_color='FFE6E6', fill_type='solid')
        expiring_fill = PatternFill(start_color='FFF2CC', end_color='FFF2CC', fill_type='solid')
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        # Title section
        info_font = Font(name='Arial', size=10)
        current_row = 1
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                ws.merge_cells(f'A{current_row}:D{current_row}')
                ws[f'A{current_row}'] = pharmacy.pharmaname
                ws[f'A{current_row}'].font = title_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorname:
                ws.merge_cells(f'A{current_row}:D{current_row}')
                ws[f'A{current_row}'] = f"Proprietor: {pharmacy.proprietorname}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorcontact:
                ws.merge_cells(f'A{current_row}:D{current_row}')
                ws[f'A{current_row}'] = f"Contact: {pharmacy.proprietorcontact}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietoremail:
                ws.merge_cells(f'A{current_row}:D{current_row}')
                ws[f'A{current_row}'] = f"Email: {pharmacy.proprietoremail}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.pharmaweburl:
                ws.merge_cells(f'A{current_row}:D{current_row}')
                ws[f'A{current_row}'] = f"Website: {pharmacy.pharmaweburl}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            current_row += 1
        
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = "Date-wise Inventory Report"
        ws[f'A{current_row}'].font = title_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        ws.merge_cells(f'A{current_row}:D{current_row}')
        ws[f'A{current_row}'] = f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}"
        ws[f'A{current_row}'].font = info_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        if expiry_from and expiry_to:
            ws.merge_cells(f'A{current_row}:D{current_row}')
            ws[f'A{current_row}'] = f"Entry Date Filter: {expiry_from} to {expiry_to}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        elif expiry_from:
            ws.merge_cells(f'A{current_row}:D{current_row}')
            ws[f'A{current_row}'] = f"Entry Date From: {expiry_from}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        elif expiry_to:
            ws.merge_cells(f'A{current_row}:D{current_row}')
            ws[f'A{current_row}'] = f"Entry Date To: {expiry_to}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        
        if search_query:
            ws.merge_cells(f'A{current_row}:D{current_row}')
            ws[f'A{current_row}'] = f"Search Filter: {search_query}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        
        current_row += 1  # Empty row

        # Summary section
        total_products = sum(len(group['products']) for group in expiry_data)
        
        summary_headers = ['Total Products', 'Total Inventory Value', 'Expiry Groups']
        summary_values = [total_products, f"₹{total_value:,.2f}", len(expiry_data)]
        
        # Summary headers
        for col, header in enumerate(summary_headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        # Summary values
        for col, value in enumerate(summary_values, 1):
            cell = ws.cell(row=current_row, column=col, value=value)
            cell.font = data_font
            cell.fill = summary_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 2  # Empty row
        
        # Data headers - 4 columns matching HTML template
        headers = ['Product Name', 'Purchase Rate', 'MRP', 'Stock Value']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        # Data rows grouped by expiry
        for expiry_group in expiry_data:
            # Group header row
            expiry_display = expiry_group['expiry_display']
            group_value = expiry_group['total_value']
            days_info = ""
            
            if expiry_group.get('days_to_expiry') is not None:
                days = expiry_group['days_to_expiry']
                if days < 0:
                    days_info = f" (Expired {abs(days)} days ago)"
                elif days == 0:
                    days_info = " (Expires today)"
                else:
                    days_info = f" ({days} days remaining)"
            
            # Determine fill color based on expiry status
            row_fill = None
            if expiry_group.get('days_to_expiry') is not None:
                days = expiry_group['days_to_expiry']
                if days < 0:
                    row_fill = expired_fill  # Expired
                elif days <= 30:
                    row_fill = expiring_fill  # Expiring soon
            
            # Products in this group - 4 columns
            for product in expiry_group['products']:
                row_data = [
                    product['product_name'],
                    f"₹{product['purchase_rate']:.2f}",
                    f"₹{product['mrp']:.2f}",
                    f"₹{product['value']:.2f}"
                ]
                
                for col, value in enumerate(row_data, 1):
                    cell = ws.cell(row=current_row, column=col, value=value)
                    cell.font = data_font
                    cell.border = thin_border
                    
                    if row_fill:
                        cell.fill = row_fill
                    
                    # Alignment
                    if col in [2, 3, 4]:  # Numeric columns
                        cell.alignment = Alignment(horizontal='right')
                    else:
                        cell.alignment = Alignment(horizontal='left')
                
                current_row += 1
            
            current_row += 1  # Empty row between groups
        
        # Auto-adjust column widths - 4 columns
        column_widths = [40, 18, 18, 18]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"dateexpiry_inventory_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)


@login_required
def export_all_product_inventory_pdf(request):
    """Export all product inventory as PDF"""
    from django.db.models import Sum
    from .models import ProductInventoryCache, BatchInventoryCache
    
    try:
        search_query = request.GET.get('search', '').strip()
        
        # Get products
        products = ProductMaster.objects.all()
        if search_query:
            products = products.filter(
                Q(product_name__icontains=search_query) |
                Q(product_company__icontains=search_query)
            )
        
        products = products.order_by('product_name')
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            topMargin=0.5*inch,
            bottomMargin=0.5*inch,
            leftMargin=0.5*inch,
            rightMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None
        
        # Styles
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=8, alignment=TA_CENTER, textColor=colors.darkblue)
        info_style = ParagraphStyle('InfoStyle', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, spaceAfter=4)
        date_style = ParagraphStyle('DateStyle', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=6)
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                story.append(Paragraph(f"{pharmacy.pharmaname}", title_style))
            if pharmacy.proprietorname:
                story.append(Paragraph(f"Proprietor: {pharmacy.proprietorname}", info_style))
            if pharmacy.proprietorcontact:
                story.append(Paragraph(f"Contact: {pharmacy.proprietorcontact}", info_style))
            story.append(Spacer(1, 0.1*inch))
        
        story.append(Paragraph("All Products Inventory Report", title_style))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}", date_style))
        
        if search_query:
            story.append(Paragraph(f"Search Filter: {search_query}", date_style))
        
        story.append(Spacer(1, 0.2*inch))
        
        # Collect inventory data
        inventory_data = []
        total_stock = 0
        total_value = 0
        
        for product in products:
            try:
                cache = ProductInventoryCache.objects.get(product_id=product.productid)
                # Use total_stock which includes current_stock + current_free_qty
                current_stock = cache.total_stock
                stock_value = cache.total_stock_value
            except ProductInventoryCache.DoesNotExist:
                current_stock = 0
                stock_value = 0
            
            if current_stock > 0:
                inventory_data.append({
                    'product_name': product.product_name,
                    'product_company': product.product_company,
                    'product_packing': product.product_packing,
                    'current_stock': current_stock,
                    'stock_value': stock_value
                })
                
                total_stock += current_stock
                total_value += stock_value
        
        # Summary
        summary_data = [
            ['Total Products', 'Total Stock', 'Total Value'],
            [str(len(inventory_data)), str(int(total_stock)), f"₹{total_value:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('FONT', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # Data table
        if inventory_data:
            table_data = [['Product Name', 'Company', 'Packing', 'Stock Qty', 'Stock Value']]
            
            for item in inventory_data:
                table_data.append([
                    item['product_name'][:30] + '...' if len(item['product_name']) > 30 else item['product_name'],
                    item['product_company'][:20] + '...' if len(item['product_company']) > 20 else item['product_company'],
                    item['product_packing'][:15] + '...' if len(item['product_packing']) > 15 else item['product_packing'],
                    str(int(item['current_stock'])),
                    f"₹{item['stock_value']:.2f}"
                ])
            
            col_widths = [3*inch, 2*inch, 1.5*inch, 1.2*inch, 1.5*inch]
            inventory_table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            inventory_table.setStyle(TableStyle([
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONT', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ]))
            
            story.append(inventory_table)
        else:
            story.append(Paragraph("No inventory data found.", styles['Normal']))
        
        doc.build(story)
        
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        filename = f"all_product_inventory_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating PDF: {str(e)}", status=500)


@login_required
def export_all_product_inventory_excel(request):
    """Export all product inventory as Excel"""
    from django.db.models import Sum
    from .models import ProductInventoryCache, BatchInventoryCache
    
    try:
        search_query = request.GET.get('search', '').strip()
        
        # Get products
        products = ProductMaster.objects.all()
        if search_query:
            products = products.filter(
                Q(product_name__icontains=search_query) |
                Q(product_company__icontains=search_query)
            )
        
        products = products.order_by('product_name')
        
        # Create workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "All Products Inventory"
        
        # Get pharmacy details
        try:
            pharmacy = Pharmacy_Details.objects.first()
        except:
            pharmacy = None
        
        # Styles
        title_font = Font(name='Arial', size=14, bold=True, color='1F4E79')
        header_font = Font(name='Arial', size=11, bold=True, color='FFFFFF')
        data_font = Font(name='Arial', size=10)
        
        header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
        summary_fill = PatternFill(start_color='E7F3FF', end_color='E7F3FF', fill_type='solid')
        
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        current_row = 1
        info_font = Font(name='Arial', size=10)
        
        # Pharmacy details
        if pharmacy:
            if pharmacy.pharmaname:
                ws.merge_cells(f'A{current_row}:F{current_row}')
                ws[f'A{current_row}'] = pharmacy.pharmaname
                ws[f'A{current_row}'].font = title_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorname:
                ws.merge_cells(f'A{current_row}:F{current_row}')
                ws[f'A{current_row}'] = f"Proprietor: {pharmacy.proprietorname}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            if pharmacy.proprietorcontact:
                ws.merge_cells(f'A{current_row}:F{current_row}')
                ws[f'A{current_row}'] = f"Contact: {pharmacy.proprietorcontact}"
                ws[f'A{current_row}'].font = info_font
                ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
                current_row += 1
            current_row += 1
        
        ws.merge_cells(f'A{current_row}:F{current_row}')
        ws[f'A{current_row}'] = "All Products Inventory Report"
        ws[f'A{current_row}'].font = title_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        ws.merge_cells(f'A{current_row}:F{current_row}')
        ws[f'A{current_row}'] = f"Generated on: {datetime.now().strftime('%d %B %Y at %H:%M')}"
        ws[f'A{current_row}'].font = info_font
        ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
        current_row += 1
        
        if search_query:
            ws.merge_cells(f'A{current_row}:F{current_row}')
            ws[f'A{current_row}'] = f"Search Filter: {search_query}"
            ws[f'A{current_row}'].font = info_font
            ws[f'A{current_row}'].alignment = Alignment(horizontal='center')
            current_row += 1
        
        current_row += 1
        
        # Collect inventory data
        inventory_data = []
        total_stock = 0
        total_value = 0
        
        for product in products:
            try:
                cache = ProductInventoryCache.objects.get(product_id=product.productid)
                # Use total_stock which includes current_stock + current_free_qty
                current_stock = cache.total_stock
                stock_value = cache.total_stock_value
            except ProductInventoryCache.DoesNotExist:
                current_stock = 0
                stock_value = 0
            
            if current_stock > 0:
                inventory_data.append({
                    'product_name': product.product_name,
                    'product_company': product.product_company,
                    'product_packing': product.product_packing,
                    'current_stock': current_stock,
                    'stock_value': stock_value
                })
                
                total_stock += current_stock
                total_value += stock_value
        
        # Summary
        summary_headers = ['Total Products', 'Total Stock', 'Total Value']
        summary_values = [len(inventory_data), int(total_stock), f"₹{total_value:,.2f}"]
        
        for col, header in enumerate(summary_headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        for col, value in enumerate(summary_values, 1):
            cell = ws.cell(row=current_row, column=col, value=value)
            cell.font = data_font
            cell.fill = summary_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 2
        
        # Data headers
        headers = ['Product Name', 'Company', 'Packing', 'Stock Qty', 'Stock Value']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=current_row, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = thin_border
        current_row += 1
        
        # Data rows
        for item in inventory_data:
            row_data = [
                item['product_name'],
                item['product_company'],
                item['product_packing'],
                int(item['current_stock']),
                f"₹{item['stock_value']:.2f}"
            ]
            
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=current_row, column=col, value=value)
                cell.font = data_font
                cell.border = thin_border
                
                if col in [4, 5]:
                    cell.alignment = Alignment(horizontal='right')
                else:
                    cell.alignment = Alignment(horizontal='left')
            
            current_row += 1
        
        # Auto-adjust column widths
        column_widths = [35, 25, 20, 15, 18]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = width
        
        # Create response
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f"all_product_inventory_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        wb.save(response)
        return response
        
    except Exception as e:
        return HttpResponse(f"Error generating Excel: {str(e)}", status=500)
