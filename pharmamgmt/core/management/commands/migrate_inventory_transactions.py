# Migration script to populate InventoryTransaction from existing data
# Run this as: python manage.py migrate_inventory_transactions

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    InventoryTransaction, PurchaseMaster, SalesMaster, 
    ReturnPurchaseMaster, ReturnSalesMaster,
    SupplierChallanMaster, CustomerChallanMaster,
    StockIssueDetail, Web_User
)
from decimal import Decimal
from datetime import datetime


class Command(BaseCommand):
    help = 'Migrate existing purchase/sales data to InventoryTransaction table'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing inventory transactions before migration',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting Inventory Transaction Migration...'))
        
        # Clear existing transactions if requested
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing inventory transactions...'))
            InventoryTransaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ Cleared existing transactions'))
        
        # Get admin user for created_by field
        admin_user = Web_User.objects.filter(user_type='admin').first()
        
        stats = {
            'purchases': 0,
            'sales': 0,
            'purchase_returns': 0,
            'sales_returns': 0,
            'supplier_challans': 0,
            'customer_challans': 0,
            'stock_issues': 0,
            'errors': 0
        }
        
        # 1. Migrate Purchase Data
        self.stdout.write('\n1. Migrating Purchase Data...')
        purchases = PurchaseMaster.objects.all().select_related('productid', 'product_invoiceid')
        
        for purchase in purchases:
            try:
                with transaction.atomic():
                    # Create transaction for paid quantity
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
                            reference_id=purchase.product_invoiceid.invoiceid,
                            reference_number=purchase.product_invoice_no,
                            rate=Decimal(str(purchase.product_purchase_rate)),
                            mrp=Decimal(str(purchase.product_MRP)),
                            total_value=Decimal(str(purchase.total_amount)),
                            created_by=admin_user,
                            remarks=f'Migrated from Purchase ID: {purchase.purchaseid}'
                        )
                        stats['purchases'] += 1
                        
                        if stats['purchases'] % 100 == 0:
                            self.stdout.write(f'  Processed {stats["purchases"]} purchases...')
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in purchase {purchase.purchaseid}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["purchases"]} purchases'))
        
        # 2. Migrate Sales Data
        self.stdout.write('\n2. Migrating Sales Data...')
        sales = SalesMaster.objects.all().select_related('productid', 'sales_invoice_no')
        
        for sale in sales:
            try:
                with transaction.atomic():
                    # Create transaction for sold quantity (negative)
                    if sale.sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=sale.productid,
                            batch_no=sale.product_batch_no,
                            expiry_date=sale.product_expiry,
                            transaction_type='SALE',
                            quantity=Decimal(str(-sale.sale_quantity)),  # Negative for OUT
                            free_quantity=Decimal(str(-sale.sale_free_qty or 0)),  # Negative for OUT
                            transaction_date=sale.sale_entry_date,
                            reference_type='INVOICE',
                            reference_id=sale.id,
                            reference_number=sale.sales_invoice_no.sales_invoice_no,
                            rate=Decimal(str(sale.sale_rate)),
                            mrp=Decimal(str(sale.product_MRP)),
                            total_value=Decimal(str(sale.sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Migrated from Sales ID: {sale.id}'
                        )
                        stats['sales'] += 1
                        
                        if stats['sales'] % 100 == 0:
                            self.stdout.write(f'  Processed {stats["sales"]} sales...')
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in sale {sale.id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["sales"]} sales'))
        
        # 3. Migrate Purchase Returns
        self.stdout.write('\n3. Migrating Purchase Returns...')
        purchase_returns = ReturnPurchaseMaster.objects.all().select_related('returnproductid', 'returninvoiceid')
        
        for ret in purchase_returns:
            try:
                with transaction.atomic():
                    # Purchase return = stock going OUT (negative)
                    if ret.returnproduct_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=ret.returnproductid,
                            batch_no=ret.returnproduct_batch_no,
                            expiry_date=ret.returnproduct_expiry.strftime('%m-%Y') if ret.returnproduct_expiry else '',
                            transaction_type='PURCHASE_RETURN',
                            quantity=Decimal(str(-ret.returnproduct_quantity)),  # Negative for OUT
                            free_quantity=Decimal(str(-ret.returnproduct_free_qty or 0)),  # Negative for OUT
                            transaction_date=ret.returnpurchase_entry_date,
                            reference_type='INVOICE',
                            reference_id=ret.returnpurchaseid,
                            reference_number=ret.returninvoiceid.returninvoiceid,
                            rate=Decimal(str(ret.returnproduct_purchase_rate)),
                            mrp=Decimal(str(ret.returnproduct_MRP)),
                            total_value=Decimal(str(ret.returntotal_amount)),
                            created_by=admin_user,
                            remarks=f'Migrated from Purchase Return ID: {ret.returnpurchaseid}'
                        )
                        stats['purchase_returns'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in purchase return {ret.returnpurchaseid}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["purchase_returns"]} purchase returns'))
        
        # 4. Migrate Sales Returns
        self.stdout.write('\n4. Migrating Sales Returns...')
        sales_returns = ReturnSalesMaster.objects.all().select_related('return_productid', 'return_sales_invoice_no')
        
        for ret in sales_returns:
            try:
                with transaction.atomic():
                    # Sales return = stock coming IN (positive)
                    if ret.return_sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=ret.return_productid,
                            batch_no=ret.return_product_batch_no,
                            expiry_date=ret.return_product_expiry,
                            transaction_type='SALES_RETURN',
                            quantity=Decimal(str(ret.return_sale_quantity)),  # Positive for IN
                            free_quantity=Decimal(str(ret.return_sale_free_qty or 0)),  # Positive for IN
                            transaction_date=ret.return_sale_entry_date,
                            reference_type='INVOICE',
                            reference_id=ret.return_sales_id,
                            reference_number=ret.return_sales_invoice_no.return_sales_invoice_no,
                            rate=Decimal(str(ret.return_sale_rate)),
                            mrp=Decimal(str(ret.return_product_MRP)),
                            total_value=Decimal(str(ret.return_sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Migrated from Sales Return ID: {ret.return_sales_id}'
                        )
                        stats['sales_returns'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in sales return {ret.return_sales_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["sales_returns"]} sales returns'))
        
        # 5. Migrate Supplier Challans (if not converted to invoices)
        self.stdout.write('\n5. Migrating Supplier Challans...')
        supplier_challans = SupplierChallanMaster.objects.all().select_related('product_id', 'product_challan_id')
        
        for challan in supplier_challans:
            try:
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
                            remarks=f'Migrated from Supplier Challan ID: {challan.challan_id}'
                        )
                        stats['supplier_challans'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in supplier challan {challan.challan_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["supplier_challans"]} supplier challans'))
        
        # 6. Migrate Customer Challans (if not converted to invoices)
        self.stdout.write('\n6. Migrating Customer Challans...')
        customer_challans = CustomerChallanMaster.objects.all().select_related('product_id', 'customer_challan_id')
        
        for challan in customer_challans:
            try:
                with transaction.atomic():
                    if challan.sale_quantity > 0:
                        InventoryTransaction.objects.create(
                            product=challan.product_id,
                            batch_no=challan.product_batch_no,
                            expiry_date=challan.product_expiry,
                            transaction_type='CUSTOMER_CHALLAN',
                            quantity=Decimal(str(-challan.sale_quantity)),  # Negative for OUT
                            free_quantity=Decimal(str(-challan.sale_free_qty or 0)),  # Negative for OUT
                            transaction_date=challan.sales_entry_date,
                            reference_type='CHALLAN',
                            reference_id=challan.customer_challan_master_id,
                            reference_number=challan.customer_challan_no,
                            rate=Decimal(str(challan.sale_rate)),
                            mrp=Decimal(str(challan.product_mrp)),
                            total_value=Decimal(str(challan.sale_total_amount)),
                            created_by=admin_user,
                            remarks=f'Migrated from Customer Challan ID: {challan.customer_challan_master_id}'
                        )
                        stats['customer_challans'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in customer challan {challan.customer_challan_master_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["customer_challans"]} customer challans'))
        
        # 7. Migrate Stock Issues
        self.stdout.write('\n7. Migrating Stock Issues...')
        stock_issues = StockIssueDetail.objects.all().select_related('product', 'issue')
        
        for issue in stock_issues:
            try:
                with transaction.atomic():
                    if issue.quantity_issued > 0:
                        InventoryTransaction.objects.create(
                            product=issue.product,
                            batch_no=issue.batch_no,
                            expiry_date=issue.expiry_date,
                            transaction_type='STOCK_ISSUE',
                            quantity=Decimal(str(-issue.quantity_issued)),  # Negative for OUT
                            free_quantity=Decimal('0'),
                            transaction_date=issue.issue.issue_date,
                            reference_type='ISSUE',
                            reference_id=issue.issue.issue_id,
                            reference_number=issue.issue.issue_no,
                            rate=Decimal(str(issue.unit_rate)),
                            mrp=Decimal(str(issue.unit_rate)),
                            total_value=Decimal(str(issue.total_amount)),
                            created_by=issue.issue.created_by,
                            remarks=f'Migrated from Stock Issue ID: {issue.detail_id} - {issue.issue.get_issue_type_display()}'
                        )
                        stats['stock_issues'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'  Error in stock issue {issue.detail_id}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'✓ Migrated {stats["stock_issues"]} stock issues'))
        
        # Print Summary
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('MIGRATION SUMMARY'))
        self.stdout.write('='*60)
        self.stdout.write(f'✓ Purchases:          {stats["purchases"]:,}')
        self.stdout.write(f'✓ Sales:              {stats["sales"]:,}')
        self.stdout.write(f'✓ Purchase Returns:   {stats["purchase_returns"]:,}')
        self.stdout.write(f'✓ Sales Returns:      {stats["sales_returns"]:,}')
        self.stdout.write(f'✓ Supplier Challans:  {stats["supplier_challans"]:,}')
        self.stdout.write(f'✓ Customer Challans:  {stats["customer_challans"]:,}')
        self.stdout.write(f'✓ Stock Issues:       {stats["stock_issues"]:,}')
        self.stdout.write('-'*60)
        total = sum([v for k, v in stats.items() if k != 'errors'])
        self.stdout.write(self.style.SUCCESS(f'TOTAL MIGRATED:       {total:,}'))
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f'⚠ Errors:             {stats["errors"]:,}'))
        
        self.stdout.write('='*60)
        self.stdout.write(self.style.SUCCESS('\n✓ Migration completed successfully!'))
        
        # Verify stock counts
        self.stdout.write('\n' + '='*60)
        self.stdout.write('VERIFICATION')
        self.stdout.write('='*60)
        total_transactions = InventoryTransaction.objects.count()
        self.stdout.write(f'Total Inventory Transactions: {total_transactions:,}')
        
        # Sample stock check
        from django.db.models import Sum
        sample_products = InventoryTransaction.objects.values('product__product_name').annotate(
            total_stock=Sum('quantity')
        ).order_by('-total_stock')[:5]
        
        self.stdout.write('\nTop 5 Products by Stock:')
        for i, prod in enumerate(sample_products, 1):
            self.stdout.write(f'{i}. {prod["product__product_name"]}: {prod["total_stock"]}')
        
        self.stdout.write('\n' + '='*60)
