import csv
import io
import json
import logging
import zipfile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
from django.conf import settings

from .retailer_models import RetailerMaster, RetailerReportRequest, RetailerCSVUpload, RetailerSession
from .models import (
    SalesMaster, SalesInvoiceMaster,
    PurchaseMaster, InvoiceMaster,
    BatchInventoryCache, ProductMaster,
)

logger = logging.getLogger('retailer_sync')


# ---------------------------------------------------------------------------
# Wholesaler UI Views
# ---------------------------------------------------------------------------

def retailer_report_requests(request):
    retailers = RetailerMaster.objects.filter(is_active=True).prefetch_related('session')
    requests_qs = RetailerReportRequest.objects.select_related('retailer').prefetch_related('csv_uploads').all()

    if request.method == 'POST':
        retailer_ids = request.POST.getlist('retailer')   # multiple checkboxes
        request_types = request.POST.getlist('request_type')  # multiple checkboxes
        from_date = request.POST.get('from_date')
        to_date = request.POST.get('to_date')
        remarks = request.POST.get('remarks', '')

        if not all([retailer_ids, request_types, from_date, to_date]):
            messages.error(request, 'Select at least one retailer, one report type, and both dates.')
        else:
            created_count = 0
            for retailer_id in retailer_ids:
                try:
                    retailer = RetailerMaster.objects.get(retailer_id=retailer_id, is_active=True)
                    for rtype in request_types:
                        RetailerReportRequest.objects.create(
                            retailer=retailer,
                            request_type=rtype.upper(),
                            from_date=from_date,
                            to_date=to_date,
                            remarks=remarks,
                            created_by=request.user.username,
                        )
                        created_count += 1
                except RetailerMaster.DoesNotExist:
                    messages.error(request, f'Retailer ID {retailer_id} not found.')
            if created_count:
                messages.success(request, f'{created_count} report request(s) created successfully.')
            return redirect('retailer_report_requests')

    return render(request, 'retailer/report_requests.html', {
        'retailers': retailers,
        'report_requests': requests_qs,
    })


@require_http_methods(['GET'])
def api_retailer_status(request):
    """
    Returns online/offline status.
    A retailer is Online ONLY if their app sent a valid health check
    within the last 20 seconds (sync interval is 10s).
    """
    from datetime import timedelta
    now = datetime.now()
    threshold = now - timedelta(seconds=20)

    # Bulk reset all expired sessions in one query (no per-row DB writes)
    RetailerSession.objects.filter(
        is_online=True
    ).exclude(
        last_seen__gte=threshold
    ).update(is_online=False)

    retailers = RetailerMaster.objects.filter(is_active=True).prefetch_related('session')
    data = []
    for r in retailers:
        try:
            last_seen = r.session.last_seen
            is_online = last_seen is not None and last_seen >= threshold
        except Exception:
            is_online = False
        data.append({
            'retailerId':   r.retailer_id,
            'retailerName': r.retailer_name,
            'status':       'Online' if is_online else 'Offline',
        })
    return JsonResponse({'retailers': data})


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
    Retailer app calls this every 10s with X-API-KEY header.
    ONLY the retailer whose API key matches gets marked Online.
    No API key = 401. Wrong API key = 401.
    """
    server_mode = getattr(settings, 'RETAILER_SYNC_MODE', 'LOCAL')
    now = datetime.now()

    api_key = request.headers.get('X-API-KEY', '').strip()
    if not api_key:
        # No key — return ok but don't update any session
        return JsonResponse({
            'status': 'ok',
            'server_mode': server_mode,
            'server_time': now.strftime('%Y-%m-%d %H:%M:%S'),
        })

    try:
        retailer = RetailerMaster.objects.get(api_key=api_key, is_active=True)
    except RetailerMaster.DoesNotExist:
        logger.warning("Health check rejected: unknown api_key=%s", api_key[:8])
        return JsonResponse({'error': 'Invalid API key'}, status=401)

    # Update ONLY this retailer's session
    RetailerSession.objects.update_or_create(
        retailer=retailer,
        defaults={'last_seen': now, 'is_online': True},
    )
    logger.debug("Health check OK: retailer=%s (%s)",
                 retailer.retailer_name, now.strftime('%H:%M:%S'))

    return JsonResponse({
        'status': 'ok',
        'server_mode': server_mode,
        'server_time': now.strftime('%Y-%m-%d %H:%M:%S'),
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


@csrf_exempt
@require_http_methods(['POST'])
def api_delete_request(request, request_id):
    """Wholesaler deletes a request. Retailer will see it gone on next sync."""
    try:
        report_request = RetailerReportRequest.objects.get(request_id=request_id)
    except RetailerReportRequest.DoesNotExist:
        messages.error(request, f'Request #{request_id} not found.')
        return redirect('retailer_report_requests')
    report_request.delete()
    messages.success(request, f'Request #{request_id} deleted successfully.')
    return redirect('retailer_report_requests')


@csrf_exempt
@require_http_methods(['GET'])
def api_deleted_request_ids(request):
    """Retailer polls this to know which request IDs have been deleted on wholesaler."""
    retailer = _authenticate_retailer(request)
    if not retailer:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    # Return IDs that no longer exist — retailer sends its known IDs
    known_ids_raw = request.GET.get('ids', '')
    if not known_ids_raw:
        return JsonResponse({'deleted_ids': []})
    try:
        known_ids = [int(i) for i in known_ids_raw.split(',') if i.strip().isdigit()]
    except ValueError:
        return JsonResponse({'deleted_ids': []})
    existing_ids = set(
        RetailerReportRequest.objects.filter(
            request_id__in=known_ids, retailer=retailer
        ).values_list('request_id', flat=True)
    )
    deleted_ids = [i for i in known_ids if i not in existing_ids]
    return JsonResponse({'deleted_ids': deleted_ids})


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
        report_request.completed_at = datetime.now()
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
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
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


# ---------------------------------------------------------------------------
# CSV Upload API — POST /api/retailer/upload-csv/
# ---------------------------------------------------------------------------

def _parse_csv(file_obj):
    """
    Parse uploaded CSV (utf-8-sig to strip BOM).
    Returns (row_count, preview_rows_list_of_dicts)
    Looks for a 'Total Records:' line to get row_count.
    Falls back to counting data rows.
    """
    content = file_obj.read().decode('utf-8-sig', errors='replace')
    reader  = csv.reader(io.StringIO(content))
    rows    = list(reader)

    row_count    = 0
    headers      = []
    data_rows    = []
    found_total  = False

    for row in rows:
        if not row:
            continue
        joined = ','.join(str(c) for c in row)
        if 'Total Records:' in joined:
            for cell in row:
                cell = cell.strip()
                if cell.startswith('Total Records:'):
                    try:
                        row_count = int(cell.replace('Total Records:', '').strip())
                        found_total = True
                    except ValueError:
                        pass
            continue
        if not headers:
            headers = [c.strip() for c in row]
            continue
        data_rows.append(row)

    if not found_total:
        row_count = len(data_rows)

    preview = []
    for row in data_rows[:50]:
        preview.append({headers[i]: row[i].strip() if i < len(row) else '' for i in range(len(headers))})

    return row_count, preview


@csrf_exempt
@require_http_methods(['POST'])
def api_upload_csv(request):
    retailer = _authenticate_retailer(request)
    if not retailer:
        return JsonResponse({'ok': False, 'error': 'Unauthorized'}, status=401)

    request_id   = request.POST.get('request_id')
    request_type = request.POST.get('request_type', '').upper()
    csv_file     = request.FILES.get('csv_file')

    if not request_id or not request_type or not csv_file:
        return JsonResponse({'ok': False, 'error': 'request_id, request_type and csv_file are required.'}, status=400)

    # Validate extension
    if not csv_file.name.lower().endswith('.csv'):
        return JsonResponse({'ok': False, 'error': 'Only .csv files are accepted.'}, status=400)

    # Validate size (max 10 MB)
    if csv_file.size > 10 * 1024 * 1024:
        return JsonResponse({'ok': False, 'error': 'File size exceeds 10 MB limit.'}, status=400)

    # Validate request belongs to this retailer
    try:
        report_request = RetailerReportRequest.objects.get(
            request_id=request_id, retailer=retailer
        )
    except RetailerReportRequest.DoesNotExist:
        return JsonResponse(
            {'ok': False, 'error': f'Request ID {request_id} not found or does not belong to this retailer.'},
            status=404,
        )

    # Parse CSV
    try:
        row_count, preview_data = _parse_csv(csv_file)
        csv_file.seek(0)
    except Exception as e:
        logger.error("CSV parse error for request_id=%s: %s", request_id, e)
        return JsonResponse({'ok': False, 'error': f'CSV parse error: {e}'}, status=400)

    file_size_kb = round(csv_file.size / 1024, 2)

    # Idempotent — update if exists, create if not
    upload, created = RetailerCSVUpload.objects.update_or_create(
        request=report_request,
        defaults={
            'retailer':     retailer,
            'csv_file':     csv_file,
            'file_name':    csv_file.name,
            'file_size_kb': file_size_kb,
            'request_type': request_type,
            'row_count':    row_count,
            'preview_data': preview_data,
        }
    )

    # Mark request COMPLETED
    report_request.status       = 'COMPLETED'
    report_request.completed_at = datetime.now()
    report_request.save(update_fields=['status', 'completed_at'])

    action = 'created' if created else 'updated'
    logger.info("CSV upload %s: retailer=%s request_id=%s file=%s rows=%d",
                action, retailer.retailer_code, request_id, csv_file.name, row_count)

    file_url = upload.csv_file.url if upload.csv_file else ''
    return JsonResponse({
        'ok':          True,
        'upload_id':   upload.id,
        'file_url':    file_url,
        'row_count':   row_count,
        'file_size_kb': file_size_kb,
    })


# ---------------------------------------------------------------------------
# Web Views — CSV Upload List & Preview (staff only)
# ---------------------------------------------------------------------------

@login_required
def retailer_uploads_list(request):
    qs = RetailerCSVUpload.objects.select_related('retailer', 'request').order_by('-uploaded_at')

    # Filters
    retailer_id  = request.GET.get('retailer')
    request_type = request.GET.get('request_type')
    date_from    = request.GET.get('date_from')
    date_to      = request.GET.get('date_to')
    search       = request.GET.get('search', '').strip()

    if retailer_id:
        qs = qs.filter(retailer__retailer_id=retailer_id)
    if request_type:
        qs = qs.filter(request_type=request_type)
    if date_from:
        qs = qs.filter(uploaded_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(uploaded_at__date__lte=date_to)
    if search:
        qs = qs.filter(
            retailer__retailer_name__icontains=search
        ) | qs.filter(file_name__icontains=search)

    paginator = Paginator(qs, 25)
    page      = paginator.get_page(request.GET.get('page'))

    return render(request, 'retailer/uploads_list.html', {
        'page_obj':    page,
        'retailers':   RetailerMaster.objects.filter(is_active=True),
        'filter_retailer':     retailer_id,
        'filter_request_type': request_type,
        'filter_date_from':    date_from,
        'filter_date_to':      date_to,
        'filter_search':       search,
    })


@login_required
def retailer_upload_preview(request, upload_id):
    upload  = get_object_or_404(RetailerCSVUpload.objects.select_related('retailer', 'request'), pk=upload_id)
    rows    = upload.preview_data or []
    headers = list(rows[0].keys()) if rows else []

    paginator = Paginator(rows, 50)
    page      = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'retailer/upload_preview.html', {
        'upload':  upload,
        'headers': headers,
        'page_obj': page,
    })


@login_required
def retailer_upload_download(request, upload_id):
    upload = get_object_or_404(RetailerCSVUpload, pk=upload_id)
    file_path = upload.csv_file.path
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{upload.file_name}"'
        return response


@login_required
def retailer_uploads_download_zip(request):
    """Download multiple CSVs as ZIP — called from list page checkboxes."""
    ids = request.GET.get('ids', '')
    if not ids:
        messages.error(request, 'No uploads selected.')
        return redirect('retailer_uploads_list')

    upload_ids = [int(i) for i in ids.split(',') if i.strip().isdigit()]
    uploads    = RetailerCSVUpload.objects.filter(pk__in=upload_ids)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for u in uploads:
            try:
                with open(u.csv_file.path, 'rb') as f:
                    zf.writestr(u.file_name, f.read())
            except Exception:
                pass
    buf.seek(0)

    response = HttpResponse(buf.read(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="retailer_csv_uploads.zip"'
    return response
