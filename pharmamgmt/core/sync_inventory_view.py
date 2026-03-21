from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from core.models import (
    InventoryTransaction, PurchaseMaster, SalesMaster, 
    ReturnPurchaseMaster, ReturnSalesMaster,
    SupplierChallanMaster, CustomerChallanMaster,
    StockIssueDetail, Web_User
)
from decimal import Decimal
import threading


@login_required
def sync_old_inventory_data(request):
    """
    Sync old purchase/sales data to InventoryTransaction table
    Runs in background thread to avoid timeout
    """
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    # Check if user is admin
    if request.user.user_type != 'admin':
        return JsonResponse({'success': False, 'error': 'Only admin can sync data'})
    
    # Start sync in background thread
    thread = threading.Thread(target=_sync_data_background, args=(request.user,))
    thread.daemon = True
    thread.start()
    
    return JsonResponse({
        'success': True,
        'message': 'Data sync started in background. This may take a few minutes. You can continue working.'
    })


def _sync_data_background(user):
    """Background function to sync data with strong duplicate prevention"""
    
    try:
        admin_user = user
        stats = {
            'purchases': 0,
            'sales': 0,
            'purchase_returns': 0,
            'sales_returns': 0,
            'supplier_challans': 0,
            'customer_challans': 0,
            'stock_issues': 0,
            'skipped': 0,
            'errors': 0
        }
        
        # STRONG DUPLICATE PREVENTION
        # Create comprehensive lookup of existing transactions
        existing_transactions = {}
        for txn in InventoryTransaction.objects.all().values(
            'product_id', 'batch_no', 'transaction_type', 
            'reference_type', 'reference_id'
        ):
            # Create unique key combining multiple fields
            key = f"{txn['product_id']}_{txn['batch_no']}_{txn['transaction_type']}_{txn['reference_type']}_{txn['reference_id']}"
            existing_transactions[key] = True
        
        # 1. Sync Purchases
        purchases = PurchaseMaster.objects.all().select_related('productid', 'product_invoiceid')
        for purchase in purchases:
            try:
                # Check if this purchase came from a supplier challan
                if purchase.source_challan_no:
                    # Find the original challan and UPDATE it to PURCHASE type
                    try:
                        challan = SupplierChallanMaster.objects.get(
                            product_challan_no=purchase.source_challan_no,
                            product_id=purchase.productid,
                            product_batch_no=purchase.product_batch_no
                        )
                        
                        # Check if challan transaction exists
                        challan_txn = InventoryTransaction.objects.filter(
                            product=challan.product_id,
                            batch_no=challan.product_batch_no,
                            transaction_type='SUPPLIER_CHALLAN',
                            reference_number=purchase.source_challan_no
                        ).first()
                        
                        if challan_txn:
                            # Update challan transaction to PURCHASE
                            challan_txn.transaction_type = 'PURCHASE'
                            challan_txn.reference_type = 'INVOICE'
                            challan_txn.reference_id = purchase.purchaseid
                            challan_txn.reference_number = purchase.product_invoice_no
                            challan_txn.transaction_date = purchase.purchase_entry_date
                            challan_txn.quantity = Decimal(str(purchase.product_quantity))
                            challan_txn.free_quantity = Decimal(str(purchase.product_free_qty or 0))
                            challan_txn.rate = Decimal(str(purchase.product_purchase_rate))
                            challan_txn.mrp = Decimal(str(purchase.product_MRP))
                            challan_txn.total_value = Decimal(str(purchase.total_amount))
                            challan_txn.remarks = f'Purchase from {purchase.product_supplierid.supplier_name} (from challan {purchase.source_challan_no})'
                            challan_txn.save()
                            stats['purchases'] += 1
                            continue
                    except SupplierChallanMaster.DoesNotExist:
                        pass
                
                # Create unique key for this purchase
                unique_key = f"{purchase.productid.productid}_{purchase.product_batch_no}_PURCHASE_INVOICE_{purchase.purchaseid}"
                
                # Skip if already exists
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if purchase.product_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=purchase.productid,
                            batch_no=purchase.product_batch_no,
                            expiry_date=purchase.product_expiry,
                            transaction_type='PURCHASE',
                            quantity=Decimal(str(purchase.product_quantity)),
                            free_quantity=Decimal(str(purchase.product_free_qty or 0)),
                            transaction_date=purchase.purchase_entry_date,
                            reference_type='INVOICE',
                            reference_id=purchase.purchaseid,
                            reference_number=purchase.product_invoice_no,
                            rate=Decimal(str(purchase.product_purchase_rate)),
                            mrp=Decimal(str(purchase.product_MRP)),
                            total_value=Decimal(str(purchase.total_amount)),
                            created_by=admin_user,
                            remarks=f'Purchase from {purchase.product_supplierid.supplier_name}'
                        )
                        stats['purchases'] += 1
                        # Add to existing set to prevent duplicates in same run
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 2. Sync Sales
        sales = SalesMaster.objects.all().select_related('productid', 'sales_invoice_no')
        for sale in sales:
            try:
                # Check if this sale came from a customer challan
                if sale.source_challan_no:
                    # Find the original challan and UPDATE it to SALE type
                    try:
                        challan = CustomerChallanMaster.objects.get(
                            customer_challan_no=sale.source_challan_no,
                            product_id=sale.productid,
                            product_batch_no=sale.product_batch_no
                        )
                        
                        # Check if challan transaction exists
                        challan_txn = InventoryTransaction.objects.filter(
                            product=challan.product_id,
                            batch_no=challan.product_batch_no,
                            transaction_type='CUSTOMER_CHALLAN',
                            reference_number=sale.source_challan_no
                        ).first()
                        
                        if challan_txn:
                            # Update challan transaction to SALE
                            challan_txn.transaction_type = 'SALE'
                            challan_txn.reference_type = 'INVOICE'
                            challan_txn.reference_id = sale.id
                            challan_txn.reference_number = sale.sales_invoice_no.sales_invoice_no
                            challan_txn.transaction_date = sale.sale_entry_date
                            challan_txn.quantity = -Decimal(str(sale.sale_quantity))
                            challan_txn.free_quantity = -Decimal(str(sale.sale_free_qty or 0))
                            challan_txn.rate = Decimal(str(sale.sale_rate))
                            challan_txn.mrp = Decimal(str(sale.product_MRP))
                            challan_txn.total_value = Decimal(str(sale.sale_total_amount))
                            challan_txn.remarks = f'Sale to {sale.customerid.customer_name} (from challan {sale.source_challan_no})'
                            challan_txn.save()
                            stats['sales'] += 1
                            continue
                    except CustomerChallanMaster.DoesNotExist:
                        pass
                
                unique_key = f"{sale.productid.productid}_{sale.product_batch_no}_SALE_INVOICE_{sale.id}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if sale.sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=sale.productid,
                            batch_no=sale.product_batch_no,
                            expiry_date=sale.product_expiry,
                            transaction_type='SALE',
                            quantity=Decimal(str(-sale.sale_quantity)),
                            free_quantity=Decimal(str(-sale.sale_free_qty or 0)),
                            transaction_date=sale.sale_entry_date,
                            reference_type='INVOICE',
                            reference_id=sale.id,
                            reference_number=sale.sales_invoice_no.sales_invoice_no,
                            rate=Decimal(str(sale.sale_rate)),
                            mrp=Decimal(str(sale.product_MRP)),
                            total_value=Decimal(str(sale.sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Sale to {sale.customerid.customer_name}'
                        )
                        stats['sales'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 3. Sync Purchase Returns
        purchase_returns = ReturnPurchaseMaster.objects.all().select_related('returnproductid', 'returninvoiceid')
        for ret in purchase_returns:
            try:
                unique_key = f"{ret.returnproductid.productid}_{ret.returnproduct_batch_no}_PURCHASE_RETURN_INVOICE_{ret.returnpurchaseid}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if ret.returnproduct_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=ret.returnproductid,
                            batch_no=ret.returnproduct_batch_no,
                            expiry_date=ret.returnproduct_expiry.strftime('%m-%Y') if ret.returnproduct_expiry else '',
                            transaction_type='PURCHASE_RETURN',
                            quantity=Decimal(str(-ret.returnproduct_quantity)),
                            free_quantity=Decimal(str(-ret.returnproduct_free_qty or 0)),
                            transaction_date=ret.returnpurchase_entry_date,
                            reference_type='INVOICE',
                            reference_id=ret.returnpurchaseid,
                            reference_number=ret.returninvoiceid.returninvoiceid,
                            rate=Decimal(str(ret.returnproduct_purchase_rate)),
                            mrp=Decimal(str(ret.returnproduct_MRP)),
                            total_value=Decimal(str(ret.returntotal_amount)),
                            created_by=admin_user,
                            remarks=f'Purchase Return to {ret.returnproduct_supplierid.supplier_name}'
                        )
                        stats['purchase_returns'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 4. Sync Sales Returns
        sales_returns = ReturnSalesMaster.objects.all().select_related('return_productid', 'return_sales_invoice_no')
        for ret in sales_returns:
            try:
                unique_key = f"{ret.return_productid.productid}_{ret.return_product_batch_no}_SALES_RETURN_INVOICE_{ret.return_sales_id}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if ret.return_sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=ret.return_productid,
                            batch_no=ret.return_product_batch_no,
                            expiry_date=ret.return_product_expiry,
                            transaction_type='SALES_RETURN',
                            quantity=Decimal(str(ret.return_sale_quantity)),
                            free_quantity=Decimal(str(ret.return_sale_free_qty or 0)),
                            transaction_date=ret.return_sale_entry_date,
                            reference_type='INVOICE',
                            reference_id=ret.return_sales_id,
                            reference_number=ret.return_sales_invoice_no.return_sales_invoice_no,
                            rate=Decimal(str(ret.return_sale_rate)),
                            mrp=Decimal(str(ret.return_product_MRP)),
                            total_value=Decimal(str(ret.return_sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Sales Return from {ret.return_customerid.customer_name}'
                        )
                        stats['sales_returns'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 5. Sync Supplier Challans (only if not converted to purchase invoice)
        supplier_challans = SupplierChallanMaster.objects.all().select_related('product_id', 'product_challan_id')
        for challan in supplier_challans:
            try:
                # Check if this challan was converted to purchase invoice
                purchase_exists = PurchaseMaster.objects.filter(
                    source_challan_no=challan.product_challan_no,
                    productid=challan.product_id,
                    product_batch_no=challan.product_batch_no
                ).exists()
                
                if purchase_exists:
                    stats['skipped'] += 1
                    continue
                
                unique_key = f"{challan.product_id.productid}_{challan.product_batch_no}_SUPPLIER_CHALLAN_CHALLAN_{challan.challan_id}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if challan.product_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=challan.product_id,
                            batch_no=challan.product_batch_no,
                            expiry_date=challan.product_expiry,
                            transaction_type='SUPPLIER_CHALLAN',
                            quantity=Decimal(str(challan.product_quantity)),
                            free_quantity=Decimal(str(challan.product_free_qty or 0)),
                            transaction_date=challan.challan_entry_date,
                            reference_type='CHALLAN',
                            reference_id=challan.challan_id,
                            reference_number=challan.product_challan_no,
                            rate=Decimal(str(challan.product_purchase_rate)),
                            mrp=Decimal(str(challan.product_mrp)),
                            total_value=Decimal(str(challan.total_amount)),
                            created_by=admin_user,
                            remarks=f'Supplier Challan from {challan.product_suppliername.supplier_name}'
                        )
                        stats['supplier_challans'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 6. Sync Customer Challans (only if not converted to sales invoice)
        customer_challans = CustomerChallanMaster.objects.all().select_related('product_id', 'customer_challan_id')
        for challan in customer_challans:
            try:
                # Check if this challan was converted to sales invoice
                sale_exists = SalesMaster.objects.filter(
                    source_challan_no=challan.customer_challan_no,
                    productid=challan.product_id,
                    product_batch_no=challan.product_batch_no
                ).exists()
                
                if sale_exists:
                    stats['skipped'] += 1
                    continue
                
                unique_key = f"{challan.product_id.productid}_{challan.product_batch_no}_CUSTOMER_CHALLAN_CHALLAN_{challan.customer_challan_master_id}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if challan.sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=challan.product_id,
                            batch_no=challan.product_batch_no,
                            expiry_date=challan.product_expiry,
                            transaction_type='CUSTOMER_CHALLAN',
                            quantity=Decimal(str(-challan.sale_quantity)),
                            free_quantity=Decimal(str(-challan.sale_free_qty or 0)),
                            transaction_date=challan.sales_entry_date,
                            reference_type='CHALLAN',
                            reference_id=challan.customer_challan_master_id,
                            reference_number=challan.customer_challan_no,
                            rate=Decimal(str(challan.sale_rate)),
                            mrp=Decimal(str(challan.product_mrp)),
                            total_value=Decimal(str(challan.sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Customer Challan to {challan.customer_name.customer_name}'
                        )
                        stats['customer_challans'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # 7. Sync Stock Issues
        stock_issues = StockIssueDetail.objects.all().select_related('product', 'issue')
        for issue in stock_issues:
            try:
                unique_key = f"{issue.product.productid}_{issue.batch_no}_STOCK_ISSUE_ISSUE_{issue.detail_id}"
                
                if unique_key in existing_transactions:
                    stats['skipped'] += 1
                    continue
                    
                with transaction.atomic():
                    if issue.quantity_issued > 0:
                        InventoryTransaction.objects.create(
                            product=issue.product,
                            batch_no=issue.batch_no,
                            expiry_date=issue.expiry_date,
                            transaction_type='STOCK_ISSUE',
                            quantity=Decimal(str(-issue.quantity_issued)),
                            free_quantity=Decimal('0'),
                            transaction_date=issue.issue.issue_date,
                            reference_type='ISSUE',
                            reference_id=issue.detail_id,
                            reference_number=issue.issue.issue_no,
                            rate=Decimal(str(issue.unit_rate)),
                            mrp=Decimal(str(issue.unit_rate)),
                            total_value=Decimal(str(issue.total_amount)),
                            created_by=issue.issue.created_by,
                            remarks=f'Stock Issue - {issue.issue.get_issue_type_display()}'
                        )
                        stats['stock_issues'] += 1
                        existing_transactions[unique_key] = True
            except Exception as e:
                stats['errors'] += 1
        
        # Log results
        print(f"Sync completed: {stats}")
        print(f"Total synced: {sum([v for k, v in stats.items() if k not in ['skipped', 'errors']])}")
        print(f"Skipped (already exists): {stats['skipped']}")
        print(f"Errors: {stats['errors']}")
        
    except Exception as e:
        print(f"Sync error: {str(e)}")
