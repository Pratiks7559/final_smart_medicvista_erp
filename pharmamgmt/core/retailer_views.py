import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings

from .retailer_models import RetailerMaster, RetailerReportRequest
from .models import (
    SalesMaster, SalesInvoiceMaster,
    PurchaseMaster, InvoiceMaster,
    BatchInventoryCache, ProductMaster,
)


# ---------------------------------------------------------------------------
# Wholesaler UI Views
# ---------------------------------------------------------------------------

def retailer_report_requests(request):
    retailers = RetailerMaster.objects.filter(is_active=True)
    requests_qs = RetailerReportRequest.objects.select_related('retailer').all()

    if request.method == 'POST':
        retailer_id = request.POST.get('retailer')
        request_type = request.POST.get('request_type')
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        remarks = request.POST.get('remarks', '')

        if not all([retailer_id, request_type, from_date, to_date]):
            messages.error(request, 'All fields except Remarks are required.')
        else:
            try:
                retailer = RetailerMaster.objects.get(retailer_id=retailer_id, is_active=True)
                RetailerReportRequest.objects.create(
                    retailer=retailer,
                    request_type=request_type,
                    from_date=from_date,
                    to_date=to_date,
                    remarks=remarks,
                    created_by=request.user.username,
                )
                messages.success(request, 'Report request created successfully.')
                return redirect('retailer_report_requests')
            except RetailerMaster.DoesNotExist:
                messages.error(request, 'Selected retailer not found.')

    return render(request, 'retailer/report_requests.html', {
        'retailers': retailers,
        'report_requests': requests_qs,
    })


def _authenticate_retailer(request):
    """Return RetailerMaster if X-API-KEY header is valid, else None."""
    api_key = request.headers.get('X-API-KEY', '').strip()
    if not api_key:
        return None
    try:
        return RetailerMaster.objects.get(api_key=api_key, is_active=True)
    except RetailerMaster.DoesNotExist:
        return None


@csrf_exempt
@require_http_methods(['GET'])
def api_health_check(request):
    """
    Unauthenticated lightweight endpoint.
    Retailer software calls this to test connectivity before syncing.
    Returns server mode so retailer can verify it connected to the right server.
    """
    server_mode = getattr(settings, 'RETAILER_SYNC_MODE', 'LOCAL')
    return JsonResponse({
        'status': 'ok',
        'server_mode': server_mode,
        'server_time': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
    })


@csrf_exempt
@require_http_methods(['GET'])
def api_pending_requests(request):
    retailer = _authenticate_retailer(request)
    if not retailer:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    pending = RetailerReportRequest.objects.filter(
        retailer=retailer, status='PENDING'
    ).values(
        'request_id', 'request_type', 'from_date', 'to_date', 'remarks', 'created_at'
    )

    data = []
    for r in pending:
        data.append({
            'request_id': r['request_id'],
            'request_type': r['request_type'],
            'from_date': str(r['from_date']),
            'to_date': str(r['to_date']),
            'remarks': r['remarks'],
            'created_at': r['created_at'].strftime('%Y-%m-%d %H:%M:%S') if r['created_at'] else None,
        })

    return JsonResponse({'requests': data})


VALID_TRANSITIONS = {
    'PENDING': ['PROCESSING'],
    'PROCESSING': ['COMPLETED', 'FAILED'],
}


@csrf_exempt
@require_http_methods(['POST'])
def api_update_status(request):
    retailer = _authenticate_retailer(request)
    if not retailer:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    request_id = body.get('request_id')
    new_status = body.get('status', '').upper()

    if not request_id or not new_status:
        return JsonResponse({'error': 'request_id and status are required'}, status=400)

    try:
        report_request = RetailerReportRequest.objects.get(
            request_id=request_id, retailer=retailer
        )
    except RetailerReportRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)

    allowed = VALID_TRANSITIONS.get(report_request.status, [])
    if new_status not in allowed:
        return JsonResponse(
            {'error': f'Cannot transition from {report_request.status} to {new_status}'},
            status=400,
        )

    report_request.status = new_status
    if new_status in ('COMPLETED', 'FAILED'):
        report_request.completed_at = timezone.now()
    report_request.save(update_fields=['status', 'completed_at'])

    return JsonResponse({'success': True, 'request_id': request_id, 'status': new_status})


@csrf_exempt
@require_http_methods(['GET'])
def api_request_data(request, request_id):
    """
    Returns structured report data for a specific request.
    The retailer calls this after receiving a pending request,
    generates PDF/Excel locally from the JSON, then calls update-status.

    Data source: wholesaler MySQL (this server) — retailer never touches it.
    """
    retailer = _authenticate_retailer(request)
    if not retailer:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        report_request = RetailerReportRequest.objects.get(
            request_id=request_id, retailer=retailer
        )
    except RetailerReportRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)

    from_date = report_request.from_date
    to_date = report_request.to_date
    rtype = report_request.request_type

    if rtype == 'SALES':
        data = _get_sales_data(from_date, to_date)
    elif rtype == 'PURCHASE':
        data = _get_purchase_data(from_date, to_date)
    elif rtype == 'STOCK':
        data = _get_stock_data()
    else:
        return JsonResponse({'error': f'Unknown report type: {rtype}'}, status=400)

    return JsonResponse({
        'request_id': report_request.request_id,
        'request_type': rtype,
        'from_date': str(from_date),
        'to_date': str(to_date),
        'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
        'data': data,
    })


# ---------------------------------------------------------------------------
# Report data query helpers — each returns a list of plain dicts
# ---------------------------------------------------------------------------

def _get_sales_data(from_date, to_date) -> list:
    rows = (
        SalesMaster.objects
        .filter(
            sales_invoice_no__sales_invoice_date__gte=from_date,
            sales_invoice_no__sales_invoice_date__lte=to_date,
        )
        .select_related('sales_invoice_no', 'customerid', 'productid')
        .order_by('sales_invoice_no__sales_invoice_date', 'sales_invoice_no')
    )
    return [
        {
            'invoice_no':       r.sales_invoice_no.sales_invoice_no,
            'invoice_date':     str(r.sales_invoice_no.sales_invoice_date),
            'customer_name':    r.customerid.customer_name,
            'customer_type':    r.customerid.customer_type,
            'product_name':     r.product_name,
            'product_company':  r.product_company,
            'product_packing':  r.product_packing,
            'batch_no':         r.product_batch_no,
            'expiry':           r.product_expiry,
            'mrp':              r.product_MRP,
            'sale_rate':        r.sale_rate,
            'quantity':         r.sale_quantity,
            'free_qty':         r.sale_free_qty,
            'discount':         r.sale_discount,
            'cgst':             r.sale_cgst,
            'sgst':             r.sale_sgst,
            'total_amount':     r.sale_total_amount,
        }
        for r in rows
    ]


def _get_purchase_data(from_date, to_date) -> list:
    rows = (
        PurchaseMaster.objects
        .filter(
            product_invoiceid__invoice_date__gte=from_date,
            product_invoiceid__invoice_date__lte=to_date,
        )
        .select_related('product_invoiceid', 'product_supplierid', 'productid')
        .order_by('product_invoiceid__invoice_date', 'product_invoice_no')
    )
    return [
        {
            'invoice_no':       r.product_invoice_no,
            'invoice_date':     str(r.product_invoiceid.invoice_date),
            'supplier_name':    r.product_supplierid.supplier_name,
            'product_name':     r.product_name,
            'product_company':  r.product_company,
            'product_packing':  r.product_packing,
            'batch_no':         r.product_batch_no,
            'expiry':           r.product_expiry,
            'mrp':              r.product_MRP,
            'purchase_rate':    r.product_purchase_rate,
            'quantity':         r.product_quantity,
            'free_qty':         r.product_free_qty,
            'discount':         r.product_discount_got,
            'cgst':             r.CGST,
            'sgst':             r.SGST,
            'total_amount':     r.total_amount,
        }
        for r in rows
    ]


def _get_stock_data() -> list:
    """Returns current batch-level stock from the inventory cache."""
    rows = (
        BatchInventoryCache.objects
        .filter(current_stock__gt=0)
        .select_related('product')
        .order_by('product__product_name', 'expiry_date', 'batch_no')
    )
    return [
        {
            'product_name':     r.product.product_name,
            'product_company':  r.product.product_company,
            'product_packing':  r.product.product_packing,
            'hsn':              r.product.product_hsn,
            'batch_no':         r.batch_no,
            'expiry':           r.expiry_date,
            'mrp':              r.mrp,
            'purchase_rate':    r.purchase_rate,
            'current_stock':    r.current_stock,
            'free_stock':       r.current_free_qty,
            'total_stock':      r.total_stock,
            'rate_a':           r.rate_a,
            'rate_b':           r.rate_b,
            'rate_c':           r.rate_c,
            'expiry_status':    r.expiry_status,
        }
        for r in rows
    ]
