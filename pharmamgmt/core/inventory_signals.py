"""
Django Signals to automatically create InventoryTransaction entries
whenever Purchase, Sale, Return, or Challan is saved
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from decimal import Decimal
from .models import (
    PurchaseMaster, SalesMaster, ReturnPurchaseMaster, ReturnSalesMaster,
    SupplierChallanMaster, CustomerChallanMaster, StockIssueDetail,
    InventoryTransaction
)


# ============================================
# PURCHASE SIGNALS
# ============================================
@receiver(post_save, sender=PurchaseMaster)
def create_inventory_transaction_for_purchase(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Purchase is saved"""
    if created:  # Only on new purchase
        try:
            # Check if this purchase came from a supplier challan (SupplierChallanMaster)
            # If yes, UPDATE the challan transaction to PURCHASE type
            if instance.source_challan_no:
                # Find and update the SupplierChallanMaster transaction
                updated = InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    transaction_type='SUPPLIER_CHALLAN',
                    reference_number=instance.source_challan_no
                ).update(
                    transaction_type='PURCHASE',
                    reference_type='INVOICE',
                    reference_id=instance.purchaseid,
                    reference_number=instance.product_invoice_no,
                    transaction_date=instance.purchase_entry_date,
                    quantity=Decimal(str(instance.product_quantity)),
                    free_quantity=Decimal(str(instance.product_free_qty)),
                    rate=Decimal(str(instance.product_purchase_rate)),
                    mrp=Decimal(str(instance.product_MRP)),
                    total_value=Decimal(str(instance.product_purchase_rate)) * Decimal(str(instance.product_quantity)),
                    remarks=f'Purchase from {instance.product_supplierid.supplier_name} (from challan {instance.source_challan_no})'
                )
                
                if updated == 0:
                    # Challan transaction not found, create new
                    InventoryTransaction.objects.create(
                        product=instance.productid,
                        batch_no=instance.product_batch_no,
                        expiry_date=instance.product_expiry,
                        transaction_type='PURCHASE',
                        quantity=Decimal(str(instance.product_quantity)),
                        free_quantity=Decimal(str(instance.product_free_qty)),
                        transaction_date=instance.purchase_entry_date,
                        reference_type='INVOICE',
                        reference_id=instance.purchaseid,
                        reference_number=instance.product_invoice_no,
                        rate=Decimal(str(instance.product_purchase_rate)),
                        mrp=Decimal(str(instance.product_MRP)),
                        total_value=Decimal(str(instance.product_purchase_rate)) * Decimal(str(instance.product_quantity)),
                        remarks=f'Purchase from {instance.product_supplierid.supplier_name}'
                    )
            else:
                # Direct purchase (not from challan)
                InventoryTransaction.objects.create(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    expiry_date=instance.product_expiry,
                    transaction_type='PURCHASE',
                    quantity=Decimal(str(instance.product_quantity)),
                    free_quantity=Decimal(str(instance.product_free_qty)),
                    transaction_date=instance.purchase_entry_date,
                    reference_type='INVOICE',
                    reference_id=instance.purchaseid,
                    reference_number=instance.product_invoice_no,
                    rate=Decimal(str(instance.product_purchase_rate)),
                    mrp=Decimal(str(instance.product_MRP)),
                    total_value=Decimal(str(instance.product_purchase_rate)) * Decimal(str(instance.product_quantity)),
                    remarks=f'Purchase from {instance.product_supplierid.supplier_name}'
                )
        except Exception as e:
            print(f"Error creating inventory transaction for purchase: {e}")


@receiver(post_delete, sender=PurchaseMaster)
def delete_inventory_transaction_for_purchase(sender, instance, **kwargs):
    """Delete or Revert InventoryTransaction when Purchase is deleted"""
    try:
        if instance.source_challan_no:
            # Get original challan data to restore quantities
            try:
                challan = SupplierChallanMaster.objects.get(
                    product_challan_no=instance.source_challan_no,
                    product_id=instance.productid,
                    product_batch_no=instance.product_batch_no
                )
                
                # First, check if challan transaction already exists
                challan_exists = InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    transaction_type='SUPPLIER_CHALLAN',
                    reference_number=instance.source_challan_no
                ).exists()
                
                if challan_exists:
                    # Challan transaction already exists, just delete the purchase transaction
                    InventoryTransaction.objects.filter(
                        product=instance.productid,
                        batch_no=instance.product_batch_no,
                        reference_type='INVOICE',
                        reference_id=instance.purchaseid,
                        transaction_type='PURCHASE'
                    ).delete()
                    print(f"Deleted purchase transaction, challan transaction already exists")
                else:
                    # REVERT back to SUPPLIER_CHALLAN with original challan quantities
                    # Use get() to ensure only ONE transaction is updated
                    try:
                        txn = InventoryTransaction.objects.get(
                            product=instance.productid,
                            batch_no=instance.product_batch_no,
                            reference_type='INVOICE',
                            reference_id=instance.purchaseid,
                            transaction_type='PURCHASE'
                        )
                        
                        # Update the transaction
                        txn.transaction_type = 'SUPPLIER_CHALLAN'
                        txn.reference_type = 'CHALLAN'
                        txn.reference_id = challan.challan_id
                        txn.reference_number = instance.source_challan_no
                        txn.quantity = Decimal(str(challan.product_quantity))
                        txn.free_quantity = Decimal(str(challan.product_free_qty))
                        txn.rate = Decimal(str(challan.product_purchase_rate))
                        txn.transaction_date = challan.challan_entry_date
                        txn.remarks = f'Supplier Challan from {instance.product_supplierid.supplier_name}'
                        txn.save()
                        print(f"Reverted purchase to challan transaction")
                        
                    except InventoryTransaction.DoesNotExist:
                        print(f"Warning: No transaction found for purchase ID {instance.purchaseid}")
                    except InventoryTransaction.MultipleObjectsReturned:
                        # If multiple found, delete all
                        InventoryTransaction.objects.filter(
                            product=instance.productid,
                            batch_no=instance.product_batch_no,
                            reference_type='INVOICE',
                            reference_id=instance.purchaseid,
                            transaction_type='PURCHASE'
                        ).delete()
                        print(f"Warning: Multiple purchase transactions found for purchase ID {instance.purchaseid}, deleted all")
                    
            except SupplierChallanMaster.DoesNotExist:
                # Challan not found, just delete the purchase transaction
                InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    reference_type='INVOICE',
                    reference_id=instance.purchaseid,
                    transaction_type='PURCHASE'
                ).delete()
        else:
            # Direct purchase - delete transaction
            InventoryTransaction.objects.filter(
                reference_type='INVOICE',
                reference_id=instance.purchaseid,
                transaction_type='PURCHASE'
            ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for purchase: {e}")


# ============================================
# SALES SIGNALS
# ============================================
@receiver(post_save, sender=SalesMaster)
def create_inventory_transaction_for_sale(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Sale is saved"""
    if created:  # Only on new sale
        try:
            # Check if this sale came from a customer challan (CustomerChallanMaster)
            # If yes, UPDATE the challan transaction to SALE type
            if instance.source_challan_no:
                # Find and update the CustomerChallanMaster transaction
                updated = InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    transaction_type='CUSTOMER_CHALLAN',
                    reference_number=instance.source_challan_no
                ).update(
                    transaction_type='SALE',
                    reference_type='INVOICE',
                    reference_id=instance.id,
                    reference_number=instance.sales_invoice_no.sales_invoice_no,
                    transaction_date=instance.sale_entry_date,
                    quantity=-Decimal(str(instance.sale_quantity)),
                    free_quantity=-Decimal(str(instance.sale_free_qty)),
                    rate=Decimal(str(instance.sale_rate)),
                    mrp=Decimal(str(instance.product_MRP)),
                    total_value=Decimal(str(instance.sale_rate)) * Decimal(str(instance.sale_quantity)),
                    remarks=f'Sale to {instance.customerid.customer_name} (from challan {instance.source_challan_no})'
                )
                
                if updated == 0:
                    # Challan transaction not found, create new
                    InventoryTransaction.objects.create(
                        product=instance.productid,
                        batch_no=instance.product_batch_no,
                        expiry_date=instance.product_expiry,
                        transaction_type='SALE',
                        quantity=-Decimal(str(instance.sale_quantity)),
                        free_quantity=-Decimal(str(instance.sale_free_qty)),
                        transaction_date=instance.sale_entry_date,
                        reference_type='INVOICE',
                        reference_id=instance.id,
                        reference_number=instance.sales_invoice_no.sales_invoice_no,
                        rate=Decimal(str(instance.sale_rate)),
                        mrp=Decimal(str(instance.product_MRP)),
                        total_value=Decimal(str(instance.sale_rate)) * Decimal(str(instance.sale_quantity)),
                        remarks=f'Sale to {instance.customerid.customer_name}'
                    )
            else:
                # Direct sale (not from challan)
                InventoryTransaction.objects.create(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    expiry_date=instance.product_expiry,
                    transaction_type='SALE',
                    quantity=-Decimal(str(instance.sale_quantity)),
                    free_quantity=-Decimal(str(instance.sale_free_qty)),
                    transaction_date=instance.sale_entry_date,
                    reference_type='INVOICE',
                    reference_id=instance.id,
                    reference_number=instance.sales_invoice_no.sales_invoice_no,
                    rate=Decimal(str(instance.sale_rate)),
                    mrp=Decimal(str(instance.product_MRP)),
                    total_value=Decimal(str(instance.sale_rate)) * Decimal(str(instance.sale_quantity)),
                    remarks=f'Sale to {instance.customerid.customer_name}'
                )
        except Exception as e:
            print(f"Error creating inventory transaction for sale: {e}")


@receiver(post_delete, sender=SalesMaster)
def delete_inventory_transaction_for_sale(sender, instance, **kwargs):
    """Delete or Revert InventoryTransaction when Sale is deleted"""
    try:
        if instance.source_challan_no:
            # Get original challan data to restore quantities
            try:
                challan = CustomerChallanMaster.objects.get(
                    customer_challan_no=instance.source_challan_no,
                    product_id=instance.productid,
                    product_batch_no=instance.product_batch_no
                )
                
                # First, check if challan transaction already exists
                challan_exists = InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    transaction_type='CUSTOMER_CHALLAN',
                    reference_number=instance.source_challan_no
                ).exists()
                
                if challan_exists:
                    # Challan transaction already exists, just delete the sale transaction
                    InventoryTransaction.objects.filter(
                        product=instance.productid,
                        batch_no=instance.product_batch_no,
                        reference_type='INVOICE',
                        reference_id=instance.id,
                        transaction_type='SALE'
                    ).delete()
                    print(f"Deleted sale transaction, challan transaction already exists")
                else:
                    # REVERT back to CUSTOMER_CHALLAN with original challan quantities
                    # Use get() to ensure only ONE transaction is updated
                    try:
                        txn = InventoryTransaction.objects.get(
                            product=instance.productid,
                            batch_no=instance.product_batch_no,
                            reference_type='INVOICE',
                            reference_id=instance.id,
                            transaction_type='SALE'
                        )
                        
                        # Update the transaction
                        txn.transaction_type = 'CUSTOMER_CHALLAN'
                        txn.reference_type = 'CHALLAN'
                        txn.reference_id = challan.customer_challan_master_id
                        txn.reference_number = instance.source_challan_no
                        txn.quantity = -Decimal(str(challan.sale_quantity))
                        txn.free_quantity = -Decimal(str(challan.sale_free_qty))
                        txn.rate = Decimal(str(challan.sale_rate))
                        txn.transaction_date = challan.sales_entry_date
                        txn.remarks = f'Customer Challan to {instance.customerid.customer_name}'
                        txn.save()
                        print(f"Reverted sale to challan transaction")
                        
                    except InventoryTransaction.DoesNotExist:
                        print(f"Warning: No transaction found for sale ID {instance.id}")
                    except InventoryTransaction.MultipleObjectsReturned:
                        # If multiple found, delete all and keep none (challan should exist separately)
                        InventoryTransaction.objects.filter(
                            product=instance.productid,
                            batch_no=instance.product_batch_no,
                            reference_type='INVOICE',
                            reference_id=instance.id,
                            transaction_type='SALE'
                        ).delete()
                        print(f"Warning: Multiple sale transactions found for sale ID {instance.id}, deleted all")
                    
            except CustomerChallanMaster.DoesNotExist:
                # Challan not found, just delete the sale transaction
                InventoryTransaction.objects.filter(
                    product=instance.productid,
                    batch_no=instance.product_batch_no,
                    reference_type='INVOICE',
                    reference_id=instance.id,
                    transaction_type='SALE'
                ).delete()
        else:
            # Direct sale - delete transaction
            InventoryTransaction.objects.filter(
                reference_type='INVOICE',
                reference_id=instance.id,
                transaction_type='SALE'
            ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for sale: {e}")


# ============================================
# PURCHASE RETURN SIGNALS
# ============================================
@receiver(post_save, sender=ReturnPurchaseMaster)
def create_inventory_transaction_for_purchase_return(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Purchase Return is saved"""
    if created:  # Only on new return
        try:
            InventoryTransaction.objects.create(
                product=instance.returnproductid,
                batch_no=instance.returnproduct_batch_no,
                expiry_date=instance.returnproduct_expiry.strftime('%m-%Y'),
                transaction_type='PURCHASE_RETURN',
                quantity=-Decimal(str(instance.returnproduct_quantity)),  # Negative for OUT
                free_quantity=-Decimal(str(instance.returnproduct_free_qty)),
                transaction_date=instance.returnpurchase_entry_date,
                reference_type='INVOICE',
                reference_id=instance.returnpurchaseid,
                reference_number=instance.returninvoiceid.returninvoiceid,
                rate=Decimal(str(instance.returnproduct_purchase_rate)),
                mrp=Decimal(str(instance.returnproduct_MRP)),
                total_value=Decimal(str(instance.returnproduct_purchase_rate)) * Decimal(str(instance.returnproduct_quantity)),
                remarks=f'Return to {instance.returnproduct_supplierid.supplier_name} - {instance.return_reason or ""}'
            )
        except Exception as e:
            print(f"Error creating inventory transaction for purchase return: {e}")


@receiver(post_delete, sender=ReturnPurchaseMaster)
def delete_inventory_transaction_for_purchase_return(sender, instance, **kwargs):
    """Delete InventoryTransaction when Purchase Return is deleted"""
    try:
        InventoryTransaction.objects.filter(
            reference_type='INVOICE',
            reference_id=instance.returnpurchaseid,
            transaction_type='PURCHASE_RETURN'
        ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for purchase return: {e}")


# ============================================
# SALES RETURN SIGNALS
# ============================================
@receiver(post_save, sender=ReturnSalesMaster)
def create_inventory_transaction_for_sales_return(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Sales Return is saved"""
    if created:  # Only on new return
        try:
            InventoryTransaction.objects.create(
                product=instance.return_productid,
                batch_no=instance.return_product_batch_no,
                expiry_date=instance.return_product_expiry,
                transaction_type='SALES_RETURN',
                quantity=Decimal(str(instance.return_sale_quantity)),  # Positive for IN
                free_quantity=Decimal(str(instance.return_sale_free_qty)),
                transaction_date=instance.return_sale_entry_date,
                reference_type='INVOICE',
                reference_id=instance.return_sales_id,
                reference_number=instance.return_sales_invoice_no.return_sales_invoice_no,
                rate=Decimal(str(instance.return_sale_rate)),
                mrp=Decimal(str(instance.return_product_MRP)),
                total_value=Decimal(str(instance.return_sale_rate)) * Decimal(str(instance.return_sale_quantity)),
                remarks=f'Return from {instance.return_customerid.customer_name} - {instance.return_reason or ""}'
            )
        except Exception as e:
            print(f"Error creating inventory transaction for sales return: {e}")


@receiver(post_delete, sender=ReturnSalesMaster)
def delete_inventory_transaction_for_sales_return(sender, instance, **kwargs):
    """Delete InventoryTransaction when Sales Return is deleted"""
    try:
        InventoryTransaction.objects.filter(
            reference_type='INVOICE',
            reference_id=instance.return_sales_id,
            transaction_type='SALES_RETURN'
        ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for sales return: {e}")


# ============================================
# SUPPLIER CHALLAN SIGNALS
# ============================================
@receiver(post_save, sender=SupplierChallanMaster)
def create_inventory_transaction_for_supplier_challan(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Supplier Challan is saved"""
    if created:  # Only on new challan
        try:
            InventoryTransaction.objects.create(
                product=instance.product_id,
                batch_no=instance.product_batch_no,
                expiry_date=instance.product_expiry,
                transaction_type='SUPPLIER_CHALLAN',
                quantity=Decimal(str(instance.product_quantity)),
                free_quantity=Decimal(str(instance.product_free_qty)),
                transaction_date=instance.challan_entry_date,
                reference_type='CHALLAN',
                reference_id=instance.challan_id,
                reference_number=instance.product_challan_no,
                rate=Decimal(str(instance.product_purchase_rate)),
                mrp=Decimal(str(instance.product_mrp)),
                total_value=Decimal(str(instance.product_purchase_rate)) * Decimal(str(instance.product_quantity)),
                remarks=f'Challan from {instance.product_suppliername.supplier_name}'
            )
        except Exception as e:
            print(f"Error creating inventory transaction for supplier challan: {e}")


@receiver(post_delete, sender=SupplierChallanMaster)
def delete_inventory_transaction_for_supplier_challan(sender, instance, **kwargs):
    """Delete InventoryTransaction when Supplier Challan is deleted"""
    try:
        InventoryTransaction.objects.filter(
            reference_type='CHALLAN',
            reference_id=instance.challan_id,
            transaction_type='SUPPLIER_CHALLAN'
        ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for supplier challan: {e}")


# ============================================
# CUSTOMER CHALLAN SIGNALS
# ============================================
@receiver(post_save, sender=CustomerChallanMaster)
def create_inventory_transaction_for_customer_challan(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Customer Challan is saved"""
    if created:  # Only on new challan
        try:
            # Ensure free_qty is not None
            free_qty = instance.sale_free_qty if instance.sale_free_qty is not None else 0
            
            InventoryTransaction.objects.create(
                product=instance.product_id,
                batch_no=instance.product_batch_no,
                expiry_date=instance.product_expiry,
                transaction_type='CUSTOMER_CHALLAN',
                quantity=-Decimal(str(instance.sale_quantity)),  # Negative for OUT
                free_quantity=-Decimal(str(free_qty)),
                transaction_date=instance.sales_entry_date,
                reference_type='CHALLAN',
                reference_id=instance.customer_challan_master_id,
                reference_number=instance.customer_challan_no,
                rate=Decimal(str(instance.sale_rate)),
                mrp=Decimal(str(instance.product_mrp)),
                total_value=Decimal(str(instance.sale_rate)) * Decimal(str(instance.sale_quantity)),
                remarks=f'Customer Challan to {instance.customer_name.customer_name}'
            )
        except Exception as e:
            print(f"Error creating inventory transaction for customer challan: {e}")


@receiver(post_delete, sender=CustomerChallanMaster)
def delete_inventory_transaction_for_customer_challan(sender, instance, **kwargs):
    """Delete InventoryTransaction when Customer Challan is deleted"""
    try:
        InventoryTransaction.objects.filter(
            reference_type='CHALLAN',
            reference_id=instance.customer_challan_master_id,
            transaction_type='CUSTOMER_CHALLAN'
        ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for customer challan: {e}")


# ============================================
# STOCK ISSUE SIGNALS
# ============================================
@receiver(post_save, sender=StockIssueDetail)
def create_inventory_transaction_for_stock_issue(sender, instance, created, **kwargs):
    """Create InventoryTransaction when Stock Issue is saved"""
    if created:  # Only on new issue
        try:
            InventoryTransaction.objects.create(
                product=instance.product,
                batch_no=instance.batch_no,
                expiry_date=instance.expiry_date,
                transaction_type='STOCK_ISSUE',
                quantity=-Decimal(str(instance.quantity_issued)),  # Negative for OUT
                free_quantity=Decimal('0'),
                transaction_date=instance.issue.issue_date,
                reference_type='ISSUE',
                reference_id=instance.detail_id,
                reference_number=instance.issue.issue_no,
                rate=Decimal(str(instance.unit_rate)),
                mrp=Decimal('0'),
                total_value=Decimal(str(instance.total_amount)),
                remarks=f'{instance.issue.get_issue_type_display()} - {instance.remarks or ""}'
            )
        except Exception as e:
            print(f"Error creating inventory transaction for stock issue: {e}")


@receiver(post_delete, sender=StockIssueDetail)
def delete_inventory_transaction_for_stock_issue(sender, instance, **kwargs):
    """Delete InventoryTransaction when Stock Issue is deleted"""
    try:
        InventoryTransaction.objects.filter(
            reference_type='ISSUE',
            reference_id=instance.detail_id,
            transaction_type='STOCK_ISSUE'
        ).delete()
    except Exception as e:
        print(f"Error deleting inventory transaction for stock issue: {e}")
