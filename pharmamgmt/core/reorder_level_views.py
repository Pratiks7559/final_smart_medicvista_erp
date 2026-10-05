from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from collections import defaultdict, namedtuple
import pandas as pd
from .models import (
    ProductMaster,
    SalesMaster,
    Pharmacy_Details,
    PurchaseMaster,
    CustomerChallanMaster,
    ReturnSalesMaster,
    InventoryTransaction,
    SaleRateMaster,
)
from .year_filter_utils import get_current_financial_year, get_financial_year_dates

ReorderStats = namedtuple('ReorderStats', ['avg_monthly_sale', 'reorder_level', 'total_available', 'reorder_needed'])
ReorderBatch = namedtuple(
    'ReorderBatch',
    [
        'product_id', 'batch_no', 'expiry_date', 'current_stock',
        'current_free_qty', 'mrp', 'purchase_rate', 'rate_a', 'rate_b', 'rate_c',
    ],
)

# ── Tunable constants ────────────────────────────────────────────────────────
LEAD_TIME_DAYS = 30   # reorder level = stock needed to cover 1 month lead time
# ─────────────────────────────────────────────────────────────────────────────


def _get_report_financial_year(request):
    current_year = get_current_financial_year()
    financial_years = list(reversed(range(2011, max(current_year, 2025) + 2)))

    try:
        selected_year = int(request.session.get('selected_year', current_year))
    except (TypeError, ValueError):
        selected_year = current_year

    requested_year = request.GET.get('financial_year')
    if requested_year:
        try:
            requested_year = int(requested_year)
        except (TypeError, ValueError):
            requested_year = None

        if requested_year in financial_years:
            selected_year = requested_year
            request.session['selected_year'] = selected_year

    if selected_year not in financial_years:
        selected_year = current_year

    return selected_year, financial_years


def _product_reorder_stats(product, batches, sales_qty, fy_start, fy_end):
    """
    Correct reorder calculations for the selected financial year.

    avg_monthly_sale = total_sales_in_fy / 12
    avg_daily_sale   = total_sales_in_fy / days_in_fy
    reorder_level    = avg_daily_sale * LEAD_TIME_DAYS
                       → minimum stock needed for the lead-time window
    total_available  = sum of current_stock and current_free_qty across batches
    reorder_needed   = max(0, reorder_level - total_available)
                       → how many units to order right now
    """
    total_sales = float(sales_qty or 0)
    days_in_window = (fy_end - fy_start).days + 1
    avg_daily_sale = total_sales / days_in_window
    avg_monthly_sale = round(total_sales / 12, 2)
    reorder_level = round(avg_daily_sale * LEAD_TIME_DAYS, 2)
    total_available = round(
        sum(float(b.current_stock) + float(b.current_free_qty) for b in batches),
        2,
    )
    reorder_needed = round(max(0.0, reorder_level - total_available), 2)

    return ReorderStats(avg_monthly_sale, reorder_level, total_available, reorder_needed)


def _financial_year_batch_sales(product_ids, fy_start, fy_end):
    """Return net FY unit demand grouped by product and exact batch."""
    sales_by_batch = defaultdict(float)
    sales_rows = SalesMaster.objects.filter(
        productid__in=product_ids,
        sales_invoice_no__sales_invoice_date__gte=fy_start,
        sales_invoice_no__sales_invoice_date__lte=fy_end,
    ).values(
        'productid', 'product_batch_no', 'product_expiry'
    ).annotate(
        total_sales=Sum('sale_quantity'),
        total_free=Sum('sale_free_qty'),
    )

    for row in sales_rows:
        product_id = row['productid']
        batch_key = (row['product_batch_no'], row['product_expiry'])
        sales_by_batch[(product_id, *batch_key)] += (
            float(row['total_sales'] or 0) + float(row['total_free'] or 0)
        )

    challan_rows = CustomerChallanMaster.objects.filter(
        product_id__in=product_ids,
        customer_challan_id__customer_challan_date__gte=fy_start,
        customer_challan_id__customer_challan_date__lte=fy_end,
    ).values(
        'product_id', 'product_batch_no', 'product_expiry'
    ).annotate(
        total_sales=Sum('sale_quantity'),
        total_free=Sum('sale_free_qty'),
    )

    for row in challan_rows:
        product_id = row['product_id']
        batch_key = (row['product_batch_no'], row['product_expiry'])
        sales_by_batch[(product_id, *batch_key)] += (
            float(row['total_sales'] or 0) + float(row['total_free'] or 0)
        )

    return_rows = ReturnSalesMaster.objects.filter(
        return_productid__in=product_ids,
        return_sales_invoice_no__return_sales_invoice_date__gte=fy_start,
        return_sales_invoice_no__return_sales_invoice_date__lte=fy_end,
    ).values(
        'return_productid', 'return_product_batch_no', 'return_product_expiry'
    ).annotate(
        total_returned=Sum('return_sale_quantity'),
        total_free_returned=Sum('return_sale_free_qty'),
    )

    for row in return_rows:
        product_id = row['return_productid']
        batch_key = (row['return_product_batch_no'], row['return_product_expiry'])
        sales_by_batch[(product_id, *batch_key)] -= (
            float(row['total_returned'] or 0)
            + float(row['total_free_returned'] or 0)
        )

    return {key: max(0.0, quantity) for key, quantity in sales_by_batch.items()}


def _financial_year_product_sales(sales_by_batch):
    sales_by_product = defaultdict(float)
    for (product_id, batch_no, expiry_date), quantity in sales_by_batch.items():
        sales_by_product[product_id] += quantity
    return sales_by_product


def _financial_year_purchased_and_sold_batches(purchase_batches, sales_by_batch):
    sold_batches_by_product = defaultdict(set)
    for (product_id, batch_no, expiry_date), quantity in sales_by_batch.items():
        if quantity > 0:
            sold_batches_by_product[product_id].add((batch_no, expiry_date))

    qualifying_batches = {}
    for product_id, batches in purchase_batches.items():
        matching_batches = batches & sold_batches_by_product.get(product_id, set())
        if matching_batches:
            qualifying_batches[product_id] = matching_batches

    qualifying_sales = {
        key: quantity
        for key, quantity in sales_by_batch.items()
        if quantity > 0
        and key[0] in qualifying_batches
        and (key[1], key[2]) in qualifying_batches[key[0]]
    }
    return qualifying_batches, qualifying_sales


def _financial_year_purchase_batches(product_ids, fy_start, fy_end):
    """Map batches by the purchase invoice date, not the line-entry timestamp."""
    purchase_batch_map = defaultdict(set)
    purchase_rows = PurchaseMaster.objects.filter(
        productid__in=product_ids,
        product_invoiceid__invoice_date__gte=fy_start,
        product_invoiceid__invoice_date__lte=fy_end,
    ).values_list('productid', 'product_batch_no', 'product_expiry').distinct()

    for product_id, batch_no, expiry_date in purchase_rows:
        purchase_batch_map[product_id].add((batch_no, expiry_date))

    return purchase_batch_map


def _financial_year_batch_inventory(product_ids, purchase_batch_map, fy_start, fy_end):
    """Build selected-FY batch rows with current stock from signed ledger entries."""
    selected_batch_metadata = {}
    purchase_rows = PurchaseMaster.objects.filter(
        productid__in=product_ids,
        product_invoiceid__invoice_date__gte=fy_start,
        product_invoiceid__invoice_date__lte=fy_end,
    ).order_by(
        'productid', 'product_batch_no', 'product_expiry',
        '-product_invoiceid__invoice_date', '-purchaseid',
    )

    sale_rates = {
        (row['productid'], row['product_batch_no']): row
        for row in SaleRateMaster.objects.filter(
            productid__in=product_ids
        ).values('productid', 'product_batch_no', 'rate_A', 'rate_B', 'rate_C')
    }

    for purchase in purchase_rows:
        key = (
            purchase.productid_id,
            purchase.product_batch_no,
            purchase.product_expiry,
        )
        if (
            (key[1], key[2]) not in purchase_batch_map.get(key[0], set())
            or key in selected_batch_metadata
        ):
            continue

        rates = sale_rates.get((key[0], key[1]), {})
        selected_batch_metadata[key] = ReorderBatch(
            product_id=key[0],
            batch_no=key[1],
            expiry_date=key[2],
            current_stock=0.0,
            current_free_qty=0.0,
            mrp=purchase.product_MRP,
            purchase_rate=purchase.product_purchase_rate,
            rate_a=rates.get('rate_A', purchase.rate_a),
            rate_b=rates.get('rate_B', purchase.rate_b),
            rate_c=rates.get('rate_C', purchase.rate_c),
        )

    transaction_rows = InventoryTransaction.objects.filter(
        product_id__in=product_ids,
    ).values(
        'product_id', 'batch_no', 'expiry_date'
    ).annotate(
        total_stock=Sum('quantity'),
        total_free_stock=Sum('free_quantity'),
    )

    for row in transaction_rows:
        key = (row['product_id'], row['batch_no'], row['expiry_date'])
        batch = selected_batch_metadata.get(key)
        if batch is None:
            continue

        selected_batch_metadata[key] = batch._replace(
            current_stock=max(0.0, float(row['total_stock'] or 0)),
            current_free_qty=max(0.0, float(row['total_free_stock'] or 0)),
        )

    batches_by_product = defaultdict(list)
    for batch in selected_batch_metadata.values():
        batches_by_product[batch.product_id].append(batch)

    for batches in batches_by_product.values():
        batches.sort(key=lambda batch: (batch.expiry_date, batch.batch_no))

    return batches_by_product


@login_required
def reorder_level_report(request):
    """Display product-wise and batch-wise reorder levels with pagination"""

    product_search    = request.GET.get('product_search', '')
    show_reorder_only = request.GET.get('show_reorder_only') == 'true'
    page_number       = request.GET.get('page', 1)
    selected_year, financial_years = _get_report_financial_year(request)
    fy_start, fy_end = get_financial_year_dates(selected_year)
    fy_label = f"FY {selected_year}-{str(selected_year + 1)[2:]}"

    products_query = ProductMaster.objects.all()

    if product_search:
        products_query = products_query.filter(
            Q(product_name__icontains=product_search) |
            Q(product_company__icontains=product_search)
        )

    product_ids = list(products_query.values_list('productid', flat=True))

    purchase_batch_map = _financial_year_purchase_batches(product_ids, fy_start, fy_end)
    sales_by_batch = _financial_year_batch_sales(product_ids, fy_start, fy_end)
    purchase_batch_map, sales_by_batch = _financial_year_purchased_and_sold_batches(
        purchase_batch_map, sales_by_batch
    )

    product_batches_map = _financial_year_batch_inventory(
        product_ids, purchase_batch_map, fy_start, fy_end
    )

    sales_by_product = _financial_year_product_sales(sales_by_batch)

    reorder_data   = []

    for product in products_query:
        batches = product_batches_map.get(product.productid, [])
        if not batches:
            continue

        sales_qty = sales_by_product.get(product.productid, 0)
        avg_monthly_sale, reorder_level, total_available, reorder_needed = \
            _product_reorder_stats(product, batches, sales_qty, fy_start, fy_end)

        if show_reorder_only and reorder_needed <= 0:
            continue

        batch_details = []
        for batch in batches:
            batch_details.append({
                'batch_no':       batch.batch_no,
                'expiry_date':    batch.expiry_date,
                'mrp':            batch.mrp,
                'purchase_rate':  batch.purchase_rate,
                'available_stock': float(batch.current_stock),
                'free_qty':       float(batch.current_free_qty),
                'net_demand_in_fy': sales_by_batch.get(
                    (product.productid, batch.batch_no, batch.expiry_date), 0
                ),
                'rate_a':         batch.rate_a,
                'rate_b':         batch.rate_b,
                'rate_c':         batch.rate_c,
            })

        reorder_data.append({
            'product_id':      product.productid,
            'product_name':    product.product_name,
            'product_company': product.product_company,
            'product_packing': product.product_packing,
            'avg_monthly_sale': avg_monthly_sale,
            'reorder_level':   reorder_level,
            'total_available': total_available,
            'reorder_needed':  reorder_needed,
            'batches':         batch_details,
            'status':          'critical' if reorder_needed > 0 else 'sufficient',
        })

    reorder_data.sort(key=lambda x: x['reorder_needed'], reverse=True)

    paginator = Paginator(reorder_data, 20)
    page_obj  = paginator.get_page(page_number)

    context = {
        'title':            'Reorder Level Report',
        'page_obj':         page_obj,
        'product_search':   product_search,
        'show_reorder_only': show_reorder_only,
        'pharmacy':         Pharmacy_Details.objects.first(),
        'total_products':   len(reorder_data),
        'lead_time_days':   LEAD_TIME_DAYS,
        'selected_year':    selected_year,
        'financial_years':  financial_years,
        'fy_label':         fy_label,
    }
    return render(request, 'purchases/reorder_level_report.html', context)


@login_required
def export_reorder_level_excel(request):
    """Export reorder level report as Excel"""

    product_search    = request.GET.get('product_search', '')
    show_reorder_only = request.GET.get('show_reorder_only') == 'true'

    selected_year, _ = _get_report_financial_year(request)
    fy_start, fy_end = get_financial_year_dates(selected_year)
    fy_label = f"FY {selected_year}-{str(selected_year + 1)[2:]}"

    products_query = ProductMaster.objects.all()
    if product_search:
        products_query = products_query.filter(
            Q(product_name__icontains=product_search) |
            Q(product_company__icontains=product_search)
        )

    data = []

    product_ids = list(products_query.values_list('productid', flat=True))
    purchase_batch_map = _financial_year_purchase_batches(product_ids, fy_start, fy_end)
    sales_by_batch = _financial_year_batch_sales(product_ids, fy_start, fy_end)
    purchase_batch_map, sales_by_batch = _financial_year_purchased_and_sold_batches(
        purchase_batch_map, sales_by_batch
    )

    product_batches_map = _financial_year_batch_inventory(
        product_ids, purchase_batch_map, fy_start, fy_end
    )

    sales_by_product = _financial_year_product_sales(sales_by_batch)

    for product in products_query:
        batches = product_batches_map.get(product.productid, [])
        if not batches:
            continue

        sales_qty = sales_by_product.get(product.productid, 0)
        avg_monthly_sale, reorder_level, total_available, reorder_needed = \
            _product_reorder_stats(product, batches, sales_qty, fy_start, fy_end)

        if show_reorder_only and reorder_needed <= 0:
            continue

        for batch in batches:
            data.append({
                'Product Name':              product.product_name,
                'Company':                   product.product_company,
                'Packing':                   product.product_packing,
                'Batch No':                  batch.batch_no,
                'Expiry':                    batch.expiry_date,
                'MRP':                       batch.mrp,
                'Purchase Rate':             batch.purchase_rate,
                'Batch Stock':               float(batch.current_stock),
                'Free Qty':                  float(batch.current_free_qty),
                'Net Demand This FY':        sales_by_batch.get(
                    (product.productid, batch.batch_no, batch.expiry_date), 0
                ),
                'Total Available':           total_available,
                'Avg Monthly Sale (FY)': avg_monthly_sale,
                f'Reorder Level ({LEAD_TIME_DAYS}d lead)': reorder_level,
                'Reorder Needed':            reorder_needed,
                'Rate A':                    batch.rate_a,
                'Rate B':                    batch.rate_b,
                'Rate C':                    batch.rate_c,
            })

    df = pd.DataFrame(data)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = (
        f'attachment; filename="reorder_level_report_{datetime.now().strftime("%Y%m%d")}.xlsx"'
    )

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Reorder Level', index=False, startrow=3)

        workbook  = writer.book
        worksheet = writer.sheets['Reorder Level']

        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter

        pharmacy = Pharmacy_Details.objects.first()
        if pharmacy:
            worksheet['A1'] = pharmacy.pharmaname.upper()
            worksheet['A1'].font      = Font(size=16, bold=True)
            worksheet['A1'].alignment = Alignment(horizontal='center')
            worksheet.merge_cells('A1:Q1')

        worksheet['A2'] = (
            f'REORDER LEVEL REPORT - {fy_label} - {datetime.now().strftime("%d-%m-%Y")} '
            f'(Avg monthly sale: FY total / 12 | Lead time: {LEAD_TIME_DAYS} days)'
        )
        worksheet['A2'].font      = Font(size=12, bold=True)
        worksheet['A2'].alignment = Alignment(horizontal='center')
        worksheet.merge_cells('A2:Q2')

        header_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
        header_font = Font(color='FFFFFF', bold=True)
        border = Border(
            left=Side(style='thin'), right=Side(style='thin'),
            top=Side(style='thin'),  bottom=Side(style='thin')
        )
        for col in range(1, 18):
            cell = worksheet.cell(row=4, column=col)
            cell.fill      = header_fill
            cell.font      = header_font
            cell.border    = border
            cell.alignment = Alignment(horizontal='center', vertical='center')

        column_widths = [25, 20, 10, 15, 10, 10, 12, 12, 10, 12, 18, 12, 20, 15, 10, 10, 10]
        for i, width in enumerate(column_widths, 1):
            worksheet.column_dimensions[get_column_letter(i)].width = width

    return response
