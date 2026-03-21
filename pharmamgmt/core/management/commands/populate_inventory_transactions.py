"""
Management command to populate InventoryTransaction table from existing data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import (
    InventoryTransaction, PurchaseMaster, SalesMaster, 
    ReturnPurchaseMaster, ReturnSalesMaster,
    SupplierChallanMaster, CustomerChallanMaster,
    StockIssueDetail
)
from decimal import Decimal


class Command(BaseCommand):
    help = 'Populate InventoryTransaction table from existing transaction data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing inventory transactions before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing inventory transactions...'))
            InventoryTransaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared!'))

        self.stdout.write(self.style.SUCCESS('Starting inventory transaction population...'))
        
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

        # Process Purchases
        self.stdout.write('Processing purchases...')
        for purchase in PurchaseMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=purchase.productid,
                    batch_no=purchase.product_batch_no,
                    expiry_date=purchase.product_expiry,
                    transaction_type='PURCHASE',
                    quantity=Decimal(str(purchase.product_quantity)),
                    free_quantity=Decimal(str(purchase.product_free_qty)),
                    transaction_date=purchase.purchase_entry_date,
                    reference_type='INVOICE',
                    reference_id=purchase.purchaseid,
                    reference_number=purchase.product_invoice_no,
                    rate=Decimal(str(purchase.product_purchase_rate)),
                    mrp=Decimal(str(purchase.product_MRP)),
                    total_value=Decimal(str(purchase.product_purchase_rate)) * Decimal(str(purchase.product_quantity)),
                    remarks=f'Purchase from {purchase.product_supplierid.supplier_name}'
                )
                stats['purchases'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in purchase {purchase.purchaseid}: {str(e)}'))

        # Process Sales
        self.stdout.write('Processing sales...')
        for sale in SalesMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=sale.productid,
                    batch_no=sale.product_batch_no,
                    expiry_date=sale.product_expiry,
                    transaction_type='SALE',
                    quantity=-Decimal(str(sale.sale_quantity)),  # Negative for OUT
                    free_quantity=-Decimal(str(sale.sale_free_qty)),
                    transaction_date=sale.sale_entry_date,
                    reference_type='INVOICE',
                    reference_id=sale.id,
                    reference_number=sale.sales_invoice_no.sales_invoice_no,
                    rate=Decimal(str(sale.sale_rate)),
                    mrp=Decimal(str(sale.product_MRP)),
                    total_value=Decimal(str(sale.sale_rate)) * Decimal(str(sale.sale_quantity)),
                    remarks=f'Sale to {sale.customerid.customer_name}'
                )
                stats['sales'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in sale {sale.id}: {str(e)}'))

        # Process Purchase Returns
        self.stdout.write('Processing purchase returns...')
        for ret in ReturnPurchaseMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=ret.returnproductid,
                    batch_no=ret.returnproduct_batch_no,
                    expiry_date=ret.returnproduct_expiry.strftime('%m-%Y'),
                    transaction_type='PURCHASE_RETURN',
                    quantity=-Decimal(str(ret.returnproduct_quantity)),  # Negative for OUT
                    free_quantity=-Decimal(str(ret.returnproduct_free_qty)),
                    transaction_date=ret.returnpurchase_entry_date,
                    reference_type='INVOICE',
                    reference_id=ret.returnpurchaseid,
                    reference_number=ret.returninvoiceid.returninvoiceid,
                    rate=Decimal(str(ret.returnproduct_purchase_rate)),
                    mrp=Decimal(str(ret.returnproduct_MRP)),
                    total_value=Decimal(str(ret.returnproduct_purchase_rate)) * Decimal(str(ret.returnproduct_quantity)),
                    remarks=f'Return to {ret.returnproduct_supplierid.supplier_name} - {ret.return_reason or ""}'
                )
                stats['purchase_returns'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in purchase return {ret.returnpurchaseid}: {str(e)}'))

        # Process Sales Returns
        self.stdout.write('Processing sales returns...')
        for ret in ReturnSalesMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=ret.return_productid,
                    batch_no=ret.return_product_batch_no,
                    expiry_date=ret.return_product_expiry,
                    transaction_type='SALES_RETURN',
                    quantity=Decimal(str(ret.return_sale_quantity)),  # Positive for IN
                    free_quantity=Decimal(str(ret.return_sale_free_qty)),
                    transaction_date=ret.return_sale_entry_date,
                    reference_type='INVOICE',
                    reference_id=ret.return_sales_id,
                    reference_number=ret.return_sales_invoice_no.return_sales_invoice_no,
                    rate=Decimal(str(ret.return_sale_rate)),
                    mrp=Decimal(str(ret.return_product_MRP)),
                    total_value=Decimal(str(ret.return_sale_rate)) * Decimal(str(ret.return_sale_quantity)),
                    remarks=f'Return from {ret.return_customerid.customer_name} - {ret.return_reason or ""}'
                )
                stats['sales_returns'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in sales return {ret.return_sales_id}: {str(e)}'))

        # Process Supplier Challans
        self.stdout.write('Processing supplier challans...')
        for challan in SupplierChallanMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=challan.product_id,
                    batch_no=challan.product_batch_no,
                    expiry_date=challan.product_expiry,
                    transaction_type='SUPPLIER_CHALLAN',
                    quantity=Decimal(str(challan.product_quantity)),
                    free_quantity=Decimal(str(challan.product_free_qty)),
                    transaction_date=challan.challan_entry_date,
                    reference_type='CHALLAN',
                    reference_id=challan.challan_id,
                    reference_number=challan.product_challan_no,
                    rate=Decimal(str(challan.product_purchase_rate)),
                    mrp=Decimal(str(challan.product_mrp)),
                    total_value=Decimal(str(challan.product_purchase_rate)) * Decimal(str(challan.product_quantity)),
                    remarks=f'Challan from {challan.product_suppliername.supplier_name}'
                )
                stats['supplier_challans'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in supplier challan {challan.challan_id}: {str(e)}'))

        # Process Customer Challans
        self.stdout.write('Processing customer challans...')
        for challan in CustomerChallanMaster.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=challan.product_id,
                    batch_no=challan.product_batch_no,
                    expiry_date=challan.product_expiry,
                    transaction_type='CUSTOMER_CHALLAN',
                    quantity=-Decimal(str(challan.sale_quantity)),  # Negative for OUT
                    free_quantity=-Decimal(str(challan.sale_free_qty)),
                    transaction_date=challan.sales_entry_date,
                    reference_type='CHALLAN',
                    reference_id=challan.customer_challan_master_id,
                    reference_number=challan.customer_challan_no,
                    rate=Decimal(str(challan.sale_rate)),
                    mrp=Decimal(str(challan.product_mrp)),
                    total_value=Decimal(str(challan.sale_rate)) * Decimal(str(challan.sale_quantity)),
                    remarks=f'Challan to {challan.customer_name.customer_name}'
                )
                stats['customer_challans'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in customer challan {challan.customer_challan_master_id}: {str(e)}'))

        # Process Stock Issues
        self.stdout.write('Processing stock issues...')
        for issue in StockIssueDetail.objects.all():
            try:
                InventoryTransaction.objects.create(
                    product=issue.product,
                    batch_no=issue.batch_no,
                    expiry_date=issue.expiry_date,
                    transaction_type='STOCK_ISSUE',
                    quantity=-Decimal(str(issue.quantity_issued)),  # Negative for OUT
                    free_quantity=Decimal('0'),
                    transaction_date=issue.issue.issue_date,
                    reference_type='ISSUE',
                    reference_id=issue.detail_id,
                    reference_number=issue.issue.issue_no,
                    rate=Decimal(str(issue.unit_rate)),
                    mrp=Decimal('0'),
                    total_value=Decimal(str(issue.total_amount)),
                    remarks=f'{issue.issue.get_issue_type_display()} - {issue.remarks or ""}'
                )
                stats['stock_issues'] += 1
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f'Error in stock issue {issue.detail_id}: {str(e)}'))

        # Print summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*50))
        self.stdout.write(self.style.SUCCESS('POPULATION COMPLETED!'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f'Purchases: {stats["purchases"]}')
        self.stdout.write(f'Sales: {stats["sales"]}')
        self.stdout.write(f'Purchase Returns: {stats["purchase_returns"]}')
        self.stdout.write(f'Sales Returns: {stats["sales_returns"]}')
        self.stdout.write(f'Supplier Challans: {stats["supplier_challans"]}')
        self.stdout.write(f'Customer Challans: {stats["customer_challans"]}')
        self.stdout.write(f'Stock Issues: {stats["stock_issues"]}')
        self.stdout.write(self.style.WARNING(f'Errors: {stats["errors"]}'))
        
        total = sum(v for k, v in stats.items() if k != 'errors')
        self.stdout.write(self.style.SUCCESS(f'\nTotal Transactions: {total}'))
        self.stdout.write(self.style.SUCCESS('='*50))
