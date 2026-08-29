import threading

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import (
    InvoicePaid, InvoiceMaster, SalesInvoiceMaster, SalesInvoicePaid,
    SupplierChallanMaster, PurchaseMaster, SalesMaster,
    SupplierAdvance, CustomerAdvance, AdvanceLedger
)
from .retailer_models import RetailerMaster, RetailerSession

# ---------------------------------------------------------------------------
# Bulk-operation cache suppression flag
# ---------------------------------------------------------------------------
# Views that do bulk_create should wrap their work like:
#
#   from core.signals import _cache_suppressed
#   _cache_suppressed.active = True
#   SalesMaster.objects.bulk_create(sales_to_create)
#   _cache_suppressed.active = False
#   # then call update_batch_cache / update_product_cache once per product
#
# This prevents N×15 DB queries when saving 10+ rows at once.
_cache_suppressed = threading.local()


def _is_suppressed():
    return getattr(_cache_suppressed, 'active', False)


# ---------------------------------------------------------------------------
# Retailer Online / Offline tracking
# ---------------------------------------------------------------------------

def _get_or_create_session(retailer):
    session, _ = RetailerSession.objects.get_or_create(retailer=retailer)
    return session


@receiver(user_logged_in)
def retailer_login_handler(sender, request, user, **kwargs):
    from django.utils import timezone as tz
    try:
        retailer = RetailerMaster.objects.get(retailer_code=user.username, is_active=True)
        session = _get_or_create_session(retailer)
        session.is_online = True
        session.last_login = tz.now()
        session.save(update_fields=['is_online', 'last_login'])
    except RetailerMaster.DoesNotExist:
        pass


@receiver(user_logged_out)
def retailer_logout_handler(sender, request, user, **kwargs):
    if user is None:
        return
    try:
        retailer = RetailerMaster.objects.get(retailer_code=user.username, is_active=True)
        session = _get_or_create_session(retailer)
        session.is_online = False
        from django.utils import timezone as tz
        session.last_logout = tz.now()
        session.save(update_fields=['is_online', 'last_logout'])
    except RetailerMaster.DoesNotExist:
        pass


# ---------------------------------------------------------------------------
# Purchase Invoice Payment Signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=InvoicePaid)
def update_invoice_payment_status_on_save(sender, instance, **kwargs):
    invoice = instance.ip_invoiceid
    total_paid = InvoicePaid.objects.filter(ip_invoiceid=invoice).aggregate(
        total=models.Sum('payment_amount')
    )['total'] or 0
    invoice.invoice_paid = total_paid
    balance = invoice.invoice_total - invoice.invoice_paid
    if balance <= 0.01:
        invoice.payment_status = 'paid'
    elif invoice.invoice_paid > 0:
        invoice.payment_status = 'partial'
    else:
        invoice.payment_status = 'pending'
    invoice.save()


@receiver(post_delete, sender=InvoicePaid)
def update_invoice_payment_status_on_delete(sender, instance, **kwargs):
    invoice = instance.ip_invoiceid
    total_paid = InvoicePaid.objects.filter(ip_invoiceid=invoice).aggregate(
        total=models.Sum('payment_amount')
    )['total'] or 0
    invoice.invoice_paid = total_paid
    balance = invoice.invoice_total - invoice.invoice_paid
    if balance <= 0.01:
        invoice.payment_status = 'paid'
    elif invoice.invoice_paid > 0:
        invoice.payment_status = 'partial'
    else:
        invoice.payment_status = 'pending'
    invoice.save()


# ---------------------------------------------------------------------------
# Sales Invoice Payment Signals
# ---------------------------------------------------------------------------

@receiver(post_save, sender=SalesInvoicePaid)
def update_sales_invoice_payment_on_save(sender, instance, **kwargs):
    invoice = instance.sales_ip_invoice_no
    total_paid = SalesInvoicePaid.objects.filter(sales_ip_invoice_no=invoice).aggregate(
        total=models.Sum('sales_payment_amount')
    )['total'] or 0
    invoice.sales_invoice_paid = total_paid
    invoice.save()


@receiver(post_delete, sender=SalesInvoicePaid)
def update_sales_invoice_payment_on_delete(sender, instance, **kwargs):
    invoice = instance.sales_ip_invoice_no
    total_paid = SalesInvoicePaid.objects.filter(sales_ip_invoice_no=invoice).aggregate(
        total=models.Sum('sales_payment_amount')
    )['total'] or 0
    invoice.sales_invoice_paid = total_paid
    invoice.save()


# ---------------------------------------------------------------------------
# Inventory Cache Update Signals
# All handlers check _is_suppressed() so bulk_create operations don't
# trigger N×15 DB queries — the view calls cache update once after bulk_create.
# ---------------------------------------------------------------------------

from .models import (
    ReturnPurchaseMaster, ReturnSalesMaster, StockIssueDetail,
    CustomerChallanMaster
)
from .inventory_cache import update_batch_cache, update_product_cache, update_all_batches_for_product


@receiver(post_save, sender=PurchaseMaster)
def update_cache_on_purchase_save(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.productid.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_save: {e}")


@receiver(post_delete, sender=PurchaseMaster)
def update_cache_on_purchase_delete(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        product_id  = instance.productid.productid
        batch_no    = instance.product_batch_no
        expiry_date = instance.product_expiry
        from .inventory_cache import calculate_batch_stock
        current_stock, current_free_qty = calculate_batch_stock(product_id, batch_no, expiry_date)
        if current_stock <= 0 and current_free_qty <= 0:
            from .models import BatchInventoryCache
            BatchInventoryCache.objects.filter(product_id=product_id, batch_no=batch_no, expiry_date=expiry_date).delete()
        else:
            update_batch_cache(product_id, batch_no, expiry_date)
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_delete: {e}")


@receiver(post_save, sender=SalesMaster)
def update_cache_on_sale_save(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.productid.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sale_save: {e}")


@receiver(post_delete, sender=SalesMaster)
def update_cache_on_sale_delete(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.productid.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sale_delete: {e}")


@receiver(post_save, sender=SupplierChallanMaster)
def update_cache_on_supplier_challan_save(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.product_id.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.product_id.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_supplier_challan_save: {e}")


@receiver(post_delete, sender=SupplierChallanMaster)
def update_cache_on_supplier_challan_delete(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        product_id  = instance.product_id.productid
        batch_no    = instance.product_batch_no
        expiry_date = instance.product_expiry
        from .inventory_cache import calculate_batch_stock
        current_stock, current_free_qty = calculate_batch_stock(product_id, batch_no, expiry_date)
        if current_stock <= 0 and current_free_qty <= 0:
            from .models import BatchInventoryCache
            BatchInventoryCache.objects.filter(product_id=product_id, batch_no=batch_no, expiry_date=expiry_date).delete()
        else:
            update_batch_cache(product_id, batch_no, expiry_date)
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_supplier_challan_delete: {e}")


@receiver(post_save, sender=CustomerChallanMaster)
def update_cache_on_customer_challan_save(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.product_id.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.product_id.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_customer_challan_save: {e}")


@receiver(post_delete, sender=CustomerChallanMaster)
def update_cache_on_customer_challan_delete(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.product_id.productid, instance.product_batch_no, instance.product_expiry)
        update_product_cache(instance.product_id.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_customer_challan_delete: {e}")


@receiver([post_save, post_delete], sender=ReturnPurchaseMaster)
def update_cache_on_purchase_return(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_all_batches_for_product(instance.returnproductid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_return: {e}")


@receiver([post_save, post_delete], sender=ReturnSalesMaster)
def update_cache_on_sales_return(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.return_productid.productid, instance.return_product_batch_no, instance.return_product_expiry)
        update_product_cache(instance.return_productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sales_return: {e}")


@receiver([post_save, post_delete], sender=StockIssueDetail)
def update_cache_on_stock_issue(sender, instance, **kwargs):
    if _is_suppressed():
        return
    try:
        update_batch_cache(instance.product.productid, instance.batch_no, instance.expiry_date)
        update_product_cache(instance.product.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_stock_issue: {e}")
