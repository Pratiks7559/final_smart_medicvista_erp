from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models
from .models import (
    InvoicePaid, InvoiceMaster, SalesInvoicePaid, SalesInvoiceMaster,
    SupplierChallanMaster, PurchaseMaster, SalesMaster
)
# REMOVED: InventoryMaster, InventoryTransaction - no longer needed

@receiver(post_save, sender=InvoicePaid)
def update_invoice_payment_status_on_save(sender, instance, **kwargs):
    """Update invoice payment status when a payment is added or modified"""
    invoice = instance.ip_invoiceid
    
    # Recalculate total paid amount from all payments
    total_paid = InvoicePaid.objects.filter(ip_invoiceid=invoice).aggregate(
        total=models.Sum('payment_amount')
    )['total'] or 0
    
    # Update invoice paid amount
    invoice.invoice_paid = total_paid
    
    # Update payment status based on balance
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
    """Update invoice payment status when a payment is deleted"""
    invoice = instance.ip_invoiceid
    
    # Recalculate total paid amount from remaining payments
    total_paid = InvoicePaid.objects.filter(ip_invoiceid=invoice).aggregate(
        total=models.Sum('payment_amount')
    )['total'] or 0
    
    # Update invoice paid amount
    invoice.invoice_paid = total_paid
    
    # Update payment status based on balance
    balance = invoice.invoice_total - invoice.invoice_paid
    if balance <= 0.01:
        invoice.payment_status = 'paid'
    elif invoice.invoice_paid > 0:
        invoice.payment_status = 'partial'
    else:
        invoice.payment_status = 'pending'
    
    invoice.save()

# Sales Invoice Payment Signals
@receiver(post_save, sender=SalesInvoicePaid)
def update_sales_invoice_payment_on_save(sender, instance, **kwargs):
    """Update sales invoice payment total when a payment is added or modified"""
    invoice = instance.sales_ip_invoice_no
    
    # Recalculate total paid amount from all payments
    total_paid = SalesInvoicePaid.objects.filter(sales_ip_invoice_no=invoice).aggregate(
        total=models.Sum('sales_payment_amount')
    )['total'] or 0
    
    # Update invoice paid amount
    invoice.sales_invoice_paid = total_paid
    invoice.save()

@receiver(post_delete, sender=SalesInvoicePaid)
def update_sales_invoice_payment_on_delete(sender, instance, **kwargs):
    """Update sales invoice payment total when a payment is deleted"""
    invoice = instance.sales_ip_invoice_no
    
    # Recalculate total paid amount from remaining payments
    total_paid = SalesInvoicePaid.objects.filter(sales_ip_invoice_no=invoice).aggregate(
        total=models.Sum('sales_payment_amount')
    )['total'] or 0
    
    # Update invoice paid amount
    invoice.sales_invoice_paid = total_paid
    invoice.save()

# REMOVED: Inventory Management Signals - no longer needed
# Inventory is now tracked through PurchaseMaster and SalesMaster tables directly

# ============================================
# INVENTORY CACHE UPDATE SIGNALS - START
# ============================================
from .models import (
    ReturnPurchaseMaster, ReturnSalesMaster, StockIssueDetail,
    CustomerChallanMaster
)
from .inventory_cache import update_batch_cache, update_product_cache, update_all_batches_for_product

@receiver(post_save, sender=PurchaseMaster)
def update_cache_on_purchase_save(sender, instance, **kwargs):
    """Update cache when purchase is added/modified"""
    try:
        update_batch_cache(
            instance.productid.productid,
            instance.product_batch_no,
            instance.product_expiry
        )
        update_product_cache(instance.productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_save: {e}")

@receiver(post_delete, sender=PurchaseMaster)
def update_cache_on_purchase_delete(sender, instance, **kwargs):
    """Update cache when purchase is deleted - recalculate from remaining records"""
    try:
        product_id = instance.productid.productid
        batch_no = instance.product_batch_no
        expiry_date = instance.product_expiry
        
        # Recalculate batch stock from remaining transactions
        from .inventory_cache import calculate_batch_stock
        current_stock, current_free_qty = calculate_batch_stock(product_id, batch_no, expiry_date)
        
        if current_stock <= 0 and current_free_qty <= 0:
            # Delete batch cache if no stock remains
            from .models import BatchInventoryCache
            BatchInventoryCache.objects.filter(
                product_id=product_id,
                batch_no=batch_no,
                expiry_date=expiry_date
            ).delete()
        else:
            # Update batch cache with recalculated stock
            update_batch_cache(product_id, batch_no, expiry_date)
        
        # Update product summary
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_delete: {e}")

@receiver(post_save, sender=SalesMaster)
def update_cache_on_sale_save(sender, instance, **kwargs):
    """Update cache when sale is added/modified"""
    try:
        update_batch_cache(
            instance.productid.productid,
            instance.product_batch_no,
            instance.product_expiry
        )
        update_product_cache(instance.productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sale_save: {e}")

@receiver(post_delete, sender=SalesMaster)
def update_cache_on_sale_delete(sender, instance, **kwargs):
    """Update cache when sale is deleted - recalculate from remaining records"""
    try:
        product_id = instance.productid.productid
        batch_no = instance.product_batch_no
        expiry_date = instance.product_expiry
        
        # Recalculate and update batch cache
        update_batch_cache(product_id, batch_no, expiry_date)
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sale_delete: {e}")

@receiver(post_save, sender=SupplierChallanMaster)
def update_cache_on_supplier_challan_save(sender, instance, **kwargs):
    """Update cache when supplier challan is added/modified"""
    try:
        update_batch_cache(
            instance.product_id.productid,
            instance.product_batch_no,
            instance.product_expiry
        )
        update_product_cache(instance.product_id.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_supplier_challan_save: {e}")

@receiver(post_delete, sender=SupplierChallanMaster)
def update_cache_on_supplier_challan_delete(sender, instance, **kwargs):
    """Update cache when supplier challan is deleted - recalculate from remaining records"""
    try:
        product_id = instance.product_id.productid
        batch_no = instance.product_batch_no
        expiry_date = instance.product_expiry
        
        # Recalculate batch stock from remaining transactions
        from .inventory_cache import calculate_batch_stock
        current_stock, current_free_qty = calculate_batch_stock(product_id, batch_no, expiry_date)
        
        if current_stock <= 0 and current_free_qty <= 0:
            # Delete batch cache if no stock remains
            from .models import BatchInventoryCache
            BatchInventoryCache.objects.filter(
                product_id=product_id,
                batch_no=batch_no,
                expiry_date=expiry_date
            ).delete()
        else:
            # Update batch cache with recalculated stock
            update_batch_cache(product_id, batch_no, expiry_date)
        
        # Update product summary
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_supplier_challan_delete: {e}")

@receiver(post_save, sender=CustomerChallanMaster)
def update_cache_on_customer_challan_save(sender, instance, **kwargs):
    """Update cache when customer challan is added/modified"""
    try:
        update_batch_cache(
            instance.product_id.productid,
            instance.product_batch_no,
            instance.product_expiry
        )
        update_product_cache(instance.product_id.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_customer_challan_save: {e}")

@receiver(post_delete, sender=CustomerChallanMaster)
def update_cache_on_customer_challan_delete(sender, instance, **kwargs):
    """Update cache when customer challan is deleted - recalculate from remaining records"""
    try:
        product_id = instance.product_id.productid
        batch_no = instance.product_batch_no
        expiry_date = instance.product_expiry
        
        # Recalculate and update batch cache
        update_batch_cache(product_id, batch_no, expiry_date)
        update_product_cache(product_id)
    except Exception as e:
        print(f"[ERROR] update_cache_on_customer_challan_delete: {e}")

@receiver([post_save, post_delete], sender=ReturnPurchaseMaster)
def update_cache_on_purchase_return(sender, instance, **kwargs):
    """Update cache when purchase return is added/modified/deleted"""
    try:
        update_all_batches_for_product(instance.returnproductid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_purchase_return: {e}")

@receiver([post_save, post_delete], sender=ReturnSalesMaster)
def update_cache_on_sales_return(sender, instance, **kwargs):
    """Update cache when sales return is added/modified/deleted"""
    try:
        update_batch_cache(
            instance.return_productid.productid,
            instance.return_product_batch_no,
            instance.return_product_expiry
        )
        update_product_cache(instance.return_productid.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_sales_return: {e}")

@receiver([post_save, post_delete], sender=StockIssueDetail)
def update_cache_on_stock_issue(sender, instance, **kwargs):
    """Update cache when stock issue is added/modified/deleted"""
    try:
        update_batch_cache(
            instance.product.productid,
            instance.batch_no,
            instance.expiry_date
        )
        update_product_cache(instance.product.productid)
    except Exception as e:
        print(f"[ERROR] update_cache_on_stock_issue: {e}")
# ============================================
# INVENTORY CACHE UPDATE SIGNALS - END
# ============================================
