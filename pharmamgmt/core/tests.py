from datetime import date
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from core import backup_views
from core import models
from core import reorder_level_views
from core import utils
from core import views


class BackupLogoutTests(SimpleTestCase):
    def test_mysqldump_is_discovered_from_system_path(self):
        with patch.dict('os.environ', {'MYSQLDUMP_PATH': ''}), \
             patch.object(backup_views.shutil, 'which', return_value='/usr/bin/mysqldump'):
            executable = backup_views.get_mysqldump_path()

        self.assertEqual(executable, '/usr/bin/mysqldump')

    def test_mysql_client_is_discovered_from_system_path(self):
        with patch.dict('os.environ', {'MYSQL_PATH': ''}), \
             patch.object(backup_views.shutil, 'which', return_value='/usr/bin/mysql'):
            executable = backup_views.get_mysql_path()

        self.assertEqual(executable, '/usr/bin/mysql')

    def test_mysql_client_does_not_use_windows_path_on_linux(self):
        with patch.dict('os.environ', {'MYSQL_PATH': ''}), \
             patch.object(backup_views.os, 'name', 'posix'), \
             patch.object(backup_views.shutil, 'which', return_value=None), \
             self.assertRaises(FileNotFoundError):
            backup_views.get_mysql_path()

    def test_logout_is_performed_when_backup_creation_fails(self):
        request = RequestFactory().post('/logout/', {'backup': 'yes'})
        with patch.object(backup_views, 'create_backup_file', side_effect=RuntimeError('dump failed')), \
               patch.object(views, 'logout') as logout_user, \
               self.assertLogs('core.views', level='ERROR'):
            response = views.logout_view(request)

        self.assertEqual(response.status_code, 500)
        self.assertIn(b'"success": false', response.content)
        logout_user.assert_called_once_with(request)


class ProductDetailStockTests(SimpleTestCase):
    def test_fy_invoice_fallback_builds_batch_stock_without_ledger_rows(self):
        transactions = MagicMock()
        transactions.filter.return_value = transactions
        transactions.exists.return_value = False
        purchases = MagicMock()
        purchases.values.return_value = [{
            'product_batch_no': 'RAB-1',
            'product_expiry': '08-2013',
            'product_quantity': 100,
            'product_free_qty': 10,
            'product_MRP': 50,
            'product_purchase_rate': 40,
        }]
        sales = MagicMock()
        sales.values.return_value = [
            {
                'product_batch_no': 'RAB-1',
                'product_expiry': '08-2013',
                'sale_quantity': 20,
                'sale_free_qty': 2,
                'product_MRP': 50,
            },
            {
                'product_batch_no': 'RAB-1',
                'product_expiry': '08-2013',
                'sale_quantity': 30,
                'sale_free_qty': 3,
                'product_MRP': 50,
            },
        ]

        with patch.object(models.InventoryTransaction.objects, 'filter', return_value=transactions), \
             patch.object(utils.PurchaseMaster.objects, 'filter', return_value=purchases) as purchase_filter, \
             patch.object(utils.SalesMaster.objects, 'filter', return_value=sales) as sales_filter:
            stock_info = utils.get_stock_status(101, date(2012, 4, 1), date(2013, 3, 31))

        purchase_filter.assert_called_once_with(
            productid=101,
            product_invoiceid__invoice_date__gte=date(2012, 4, 1),
            product_invoiceid__invoice_date__lte=date(2013, 3, 31),
        )
        sales_filter.assert_called_once_with(
            productid=101,
            sales_invoice_no__sales_invoice_date__gte=date(2012, 4, 1),
            sales_invoice_no__sales_invoice_date__lte=date(2013, 3, 31),
        )
        self.assertEqual(stock_info['purchased'], 100)
        self.assertEqual(stock_info['sold'], 50)
        self.assertEqual(stock_info['current_stock'], 50)
        self.assertEqual(stock_info['current_stock_with_free'], 55)
        self.assertEqual(stock_info['expiry_stock'][0]['batch_no'], 'RAB-1')
        self.assertEqual(stock_info['expiry_stock'][0]['total_qty'], 55)

    def test_fy_totals_use_period_movements_and_stock_uses_fy_end_balance(self):
        transactions = MagicMock()
        transactions.filter.return_value = transactions
        transactions.aggregate.side_effect = [
            {
                'purchased': 100,
                'sold': -35,
                'purchase_returns': -5,
                'sales_returns': 3,
                'stock_issues': -2,
            },
            {'quantity': 71, 'free_quantity': 7},
        ]
        batch_rows = MagicMock()
        batch_rows.order_by.return_value = [
            {
                'batch_no': 'B-OLD',
                'expiry_date': '08-2027',
                'quantity': 71,
                'free_qty': 7,
                'mrp': 50,
                'rate': 40,
            },
        ]
        transactions.values.return_value.annotate.return_value = batch_rows

        with patch.object(
            models.InventoryTransaction.objects,
            'filter',
            return_value=transactions,
        ):
            stock_info = utils.get_stock_status(101, date(2026, 4, 1), date(2027, 3, 31))

        self.assertEqual(stock_info['purchased'], 100)
        self.assertEqual(stock_info['sold'], 35)
        self.assertEqual(stock_info['current_stock'], 71)
        self.assertEqual(stock_info['current_stock_with_free'], 78)
        self.assertEqual(stock_info['expiry_stock'][0]['total_qty'], 78)


class ReorderLevelReportTests(SimpleTestCase):
    def test_purchase_batch_fy_uses_invoice_date_not_line_entry_date(self):
        purchase_queryset = MagicMock()
        purchase_queryset.values_list.return_value.distinct.return_value = [
            (101, 'B-OLD', '08-2013'),
        ]

        with patch.object(
            reorder_level_views.PurchaseMaster.objects,
            'filter',
            return_value=purchase_queryset,
        ) as purchase_filter:
            batches = reorder_level_views._financial_year_purchase_batches(
                [101], date(2012, 4, 1), date(2013, 3, 31)
            )

        purchase_filter.assert_called_once_with(
            productid__in=[101],
            product_invoiceid__invoice_date__gte=date(2012, 4, 1),
            product_invoiceid__invoice_date__lte=date(2013, 3, 31),
        )
        self.assertEqual(batches, {101: {('B-OLD', '08-2013')}})

    def test_fy_sales_include_batches_purchased_in_prior_years(self):
        rows = [
            {
                'productid': 101,
                'product_batch_no': 'B-FY',
                'product_expiry': '08-2025',
                'total_sales': 7,
                'total_free': 2,
            },
            {
                'productid': 101,
                'product_batch_no': 'B-OTHER',
                'product_expiry': '08-2025',
                'total_sales': 30,
                'total_free': 0,
            },
            {
                'productid': 101,
                'product_batch_no': 'B-FY',
                'product_expiry': '08-2026',
                'total_sales': 12,
                'total_free': 0,
            },
        ]
        sales_queryset = MagicMock()
        sales_queryset.values.return_value.annotate.return_value = rows
        challan_queryset = MagicMock()
        challan_queryset.values.return_value.annotate.return_value = [{
            'product_id': 101,
            'product_batch_no': 'B-FY',
            'product_expiry': '08-2025',
            'total_sales': 1,
            'total_free': 1,
        }]
        return_queryset = MagicMock()
        return_queryset.values.return_value.annotate.return_value = [{
            'return_productid': 101,
            'return_product_batch_no': 'B-FY',
            'return_product_expiry': '08-2025',
            'total_returned': 1,
            'total_free_returned': 1,
        }]

        with patch.object(
            reorder_level_views.SalesMaster.objects,
            'filter',
            return_value=sales_queryset,
        ) as sales_filter, patch.object(
            reorder_level_views.CustomerChallanMaster.objects,
            'filter',
            return_value=challan_queryset,
        ) as challan_filter, patch.object(
            reorder_level_views.ReturnSalesMaster.objects,
            'filter',
            return_value=return_queryset,
        ) as returns_filter:
            sales_by_batch = reorder_level_views._financial_year_batch_sales(
                [101], date(2024, 4, 1), date(2025, 3, 31)
            )

        sales_filter.assert_called_once_with(
            productid__in=[101],
            sales_invoice_no__sales_invoice_date__gte=date(2024, 4, 1),
            sales_invoice_no__sales_invoice_date__lte=date(2025, 3, 31),
        )
        challan_filter.assert_called_once_with(
            product_id__in=[101],
            customer_challan_id__customer_challan_date__gte=date(2024, 4, 1),
            customer_challan_id__customer_challan_date__lte=date(2025, 3, 31),
        )
        returns_filter.assert_called_once_with(
            return_productid__in=[101],
            return_sales_invoice_no__return_sales_invoice_date__gte=date(2024, 4, 1),
            return_sales_invoice_no__return_sales_invoice_date__lte=date(2025, 3, 31),
        )
        self.assertEqual(sales_by_batch, {
            (101, 'B-FY', '08-2025'): 9.0,
            (101, 'B-OTHER', '08-2025'): 30.0,
            (101, 'B-FY', '08-2026'): 12.0,
        })
        self.assertEqual(
            reorder_level_views._financial_year_product_sales(sales_by_batch)[101],
            51.0,
        )

    def test_reorder_stats_use_fy_average_lead_time_and_free_stock(self):
        batch = MagicMock()
        batch.current_stock = 4
        batch.current_free_qty = 2

        stats = reorder_level_views._product_reorder_stats(
            None, [batch], 120, date(2024, 4, 1), date(2025, 3, 31)
        )

        self.assertEqual(stats.avg_monthly_sale, 10.0)
        self.assertEqual(stats.reorder_level, 9.86)
        self.assertEqual(stats.total_available, 6.0)
        self.assertEqual(stats.reorder_needed, 3.86)

    def test_batch_inventory_uses_exact_inventory_transaction_key(self):
        purchase = MagicMock()
        purchase.productid_id = 101
        purchase.product_batch_no = 'B-LEDGER'
        purchase.product_expiry = '08-2025'
        purchase.product_MRP = 55
        purchase.product_purchase_rate = 40
        purchase.rate_a = 45
        purchase.rate_b = 46
        purchase.rate_c = 47

        purchases = MagicMock()
        purchases.order_by.return_value = [purchase]
        rates = MagicMock()
        rates.values.return_value = [{
            'productid': 101,
            'product_batch_no': 'B-LEDGER',
            'rate_A': 50,
            'rate_B': 51,
            'rate_C': 52,
        }]
        transactions = MagicMock()
        transactions.values.return_value.annotate.return_value = [
            {
                'product_id': 101,
                'batch_no': 'B-LEDGER',
                'expiry_date': '08-2025',
                'total_stock': 6,
                'total_free_stock': 2,
            },
            {
                'product_id': 101,
                'batch_no': 'B-OTHER',
                'expiry_date': '08-2025',
                'total_stock': 99,
                'total_free_stock': 9,
            },
        ]

        with patch.object(
            reorder_level_views.PurchaseMaster.objects,
            'filter',
            return_value=purchases,
        ), patch.object(
            reorder_level_views.SaleRateMaster.objects,
            'filter',
            return_value=rates,
        ), patch.object(
            reorder_level_views.InventoryTransaction.objects,
            'filter',
            return_value=transactions,
        ) as transaction_filter:
            batches_by_product = reorder_level_views._financial_year_batch_inventory(
                [101], {101: {('B-LEDGER', '08-2025')}},
                date(2024, 4, 1), date(2025, 3, 31),
            )

        transaction_filter.assert_called_once_with(product_id__in=[101])
        batch = batches_by_product[101][0]
        self.assertEqual(batch.batch_no, 'B-LEDGER')
        self.assertEqual(batch.current_stock, 6.0)
        self.assertEqual(batch.current_free_qty, 2.0)
        self.assertEqual(batch.mrp, 55)
        self.assertEqual(batch.purchase_rate, 40)
        self.assertEqual((batch.rate_a, batch.rate_b, batch.rate_c), (50, 51, 52))

    def test_reorder_report_uses_selected_financial_year_window(self):
        request = RequestFactory().get('/reports/reorder-level/')
        request.session = {'selected_year': 2024}

        fake_batch = MagicMock()
        fake_batch.batch_no = 'B-100'
        fake_batch.expiry_date = '08-2024'
        fake_batch.mrp = 50.0
        fake_batch.purchase_rate = 40.0
        fake_batch.current_stock = 10.0
        fake_batch.current_free_qty = 0.0
        fake_batch.rate_a = 1.0
        fake_batch.rate_b = 2.0
        fake_batch.rate_c = 3.0

        fake_product = MagicMock()
        fake_product.productid = 101
        fake_product.product_name = 'Test Product'
        fake_product.product_company = 'Test Company'
        fake_product.product_packing = '10s'

        fake_batch_queryset = MagicMock()
        fake_batch_queryset.exists.return_value = True
        fake_batch_queryset.__iter__ = lambda self: iter([fake_batch])
        fake_batch_queryset.order_by.return_value = fake_batch_queryset
        fake_batch_queryset.filter.return_value = fake_batch_queryset

        fake_product.batch_caches.filter.return_value = fake_batch_queryset

        fake_queryset = MagicMock()
        fake_queryset.all.return_value = [fake_product]
        fake_queryset.filter.return_value = fake_queryset

        fake_purchase_queryset = MagicMock()
        fake_purchase_queryset.values_list.return_value.distinct.return_value = [('B-100', '08-2024')]

        with patch.object(reorder_level_views.ProductMaster.objects, 'prefetch_related', return_value=fake_queryset), \
             patch.object(reorder_level_views.PurchaseMaster.objects, 'filter', return_value=fake_purchase_queryset), \
             patch.object(reorder_level_views.Pharmacy_Details.objects, 'first', return_value=None), \
             patch.object(reorder_level_views, '_product_reorder_stats', return_value=(0, 0, 0, 0)) as mock_stats:
            reorder_level_views.reorder_level_report.__wrapped__(request)

        self.assertEqual(mock_stats.call_args[0][2], date(2024, 4, 1))
        self.assertEqual(mock_stats.call_args[0][3], date(2025, 3, 31))


class CombinedSalesInvoiceDateTests(SimpleTestCase):
    def test_invoice_outside_selected_fy_is_not_saved(self):
        request = RequestFactory().post(
            '/sales/add-with-products/',
            {'sales_invoice_date': '2024-03-31'},
        )
        request.session = {'selected_year': 2024}
        request.user = MagicMock(is_authenticated=True)

        class FormStub:
            cleaned_data = {'sales_invoice_date': date(2024, 3, 31)}
            errors = {}
            save = MagicMock()

            def is_valid(self):
                return not self.errors

            def add_error(self, field, error):
                self.errors[field] = [error]

        form = FormStub()
        with patch.object(views, 'SalesInvoiceForm', return_value=form), \
             patch.object(views.CustomerMaster.objects, 'select_related') as customers, \
             patch.object(views.ProductMaster.objects, 'only') as products, \
             patch.object(views.InvoiceSeries.objects, 'filter') as series, \
             patch.object(views.messages, 'error'), \
             patch.object(views, 'render', return_value=object()) as render:
            customers.return_value.order_by.return_value = []
            products.return_value.order_by.return_value = []
            series.return_value.order_by.return_value = []

            views.add_sales_invoice_with_products.__wrapped__(request)

        form.save.assert_not_called()
        self.assertIn('sales_invoice_date', form.errors)
        self.assertEqual(render.call_args.args[2]['fy_start'], '2024-04-01')
        self.assertEqual(render.call_args.args[2]['fy_end'], '2025-03-31')


class PurchaseReturnDateTests(SimpleTestCase):
    def test_return_outside_selected_fy_is_not_saved(self):
        request = RequestFactory().post(
            '/returns/add/',
            {'returninvoice_date': '31-03-2024'},
        )
        request.session = {'selected_year': 2024}
        request.user = MagicMock(is_authenticated=True)

        class FormStub:
            cleaned_data = {'returninvoice_date': date(2024, 3, 31)}
            errors = {}
            save = MagicMock()

            def is_valid(self):
                return not self.errors

            def add_error(self, field, error):
                self.errors[field] = [error]

        form = FormStub()
        with patch.object(views, 'PurchaseReturnInvoiceForm', return_value=form), \
             patch.object(views.transaction, 'atomic') as atomic, \
             patch.object(views.ReturnInvoiceMaster.objects, 'filter') as returns, \
             patch.object(views.SupplierMaster.objects, 'all') as suppliers, \
             patch.object(views.ProductMaster.objects, 'all') as products, \
             patch.object(views.messages, 'error'), \
             patch.object(views, 'render', return_value=object()) as render:
            atomic.return_value.__enter__.return_value = None
            atomic.return_value.__exit__.return_value = False
            returns.return_value.exists.return_value = False
            suppliers.return_value.order_by.return_value = []
            products.return_value.order_by.return_value = []

            views.add_purchase_return.__wrapped__(request)

        form.save.assert_not_called()
        self.assertIn('returninvoice_date', form.errors)
        self.assertEqual(render.call_args.args[2]['fy_start'], '2024-04-01')
        self.assertEqual(render.call_args.args[2]['fy_end'], '2025-03-31')
