from datetime import date
from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.forms.utils import ErrorDict
from django.test import RequestFactory, SimpleTestCase

from core import backup_views
from core import combined_invoice_view
from core import ledger_views
from core import models
from core import reorder_level_views
from core import utils
from core import views
from core.forms import InvoiceForm
from core.year_filter_utils import get_financial_year_label, get_financial_year_start


class CustomerLedgerSalesTotalTests(SimpleTestCase):
    def test_customer_ledger_debit_uses_discounted_invoice_total(self):
        request = RequestFactory().get(
            '/ledger/customer/1/',
            {'start_date': '2026-04-01', 'end_date': '2027-03-31'},
        )
        request.user = MagicMock(is_authenticated=True)
        customer = MagicMock(customer_name='Test Customer')
        sale = MagicMock(
            sales_invoice_date=date(2026, 6, 1),
            sales_invoice_no='SI-100',
            sales_invoice_total=675,
        )

        customer_qs = MagicMock()
        customer_qs.order_by.return_value = []
        sales_qs = MagicMock()
        sales_qs.order_by.return_value = sales_qs
        sales_qs.filter.return_value = [sale]
        payments_qs = MagicMock()
        payments_qs.order_by.return_value = payments_qs
        payments_qs.filter.return_value = []
        returns_qs = MagicMock()
        returns_qs.order_by.return_value = returns_qs
        returns_qs.filter.return_value = []
        advance_entries_qs = MagicMock()
        advance_entries_qs.order_by.return_value = advance_entries_qs
        advance_entries_qs.filter.return_value = []

        with patch.object(ledger_views.CustomerMaster.objects, 'all', return_value=customer_qs), \
             patch.object(ledger_views, 'get_object_or_404', return_value=customer), \
             patch.object(ledger_views.SalesInvoiceMaster.objects, 'filter', return_value=sales_qs), \
             patch.object(ledger_views.SalesInvoicePaid.objects, 'filter', return_value=payments_qs), \
             patch.object(ledger_views.ReturnSalesInvoiceMaster.objects, 'filter', return_value=returns_qs), \
             patch.object(ledger_views.AdvanceLedger.objects, 'filter', return_value=advance_entries_qs), \
             patch.object(ledger_views, '_customer_opening_balance', return_value=0), \
             patch.object(ledger_views.Pharmacy_Details.objects, 'first', return_value=None), \
             patch.object(ledger_views, 'render', return_value=object()) as render:
            ledger_views.customer_ledger.__wrapped__(request, customer_id=1)

        context = render.call_args.args[2]
        self.assertEqual(context['transactions'][0]['debit'], 675)
        self.assertEqual(context['total_debit'], 675)
        self.assertEqual(context['closing_balance'], 675)

    def test_unpaid_customer_invoice_appears_in_selected_financial_year(self):
        request = RequestFactory().get('/ledger/customer/1/')
        request.session = {'selected_year': 2024}
        request.user = MagicMock(is_authenticated=True)
        customer = MagicMock(customer_name='Test Customer')
        sale = MagicMock(
            sales_invoice_date=date(2024, 6, 1),
            sales_invoice_no='SI-UNPAID',
            sales_invoice_total=675,
        )

        customer_qs = MagicMock()
        customer_qs.order_by.return_value = []
        sales_qs = MagicMock()
        sales_qs.order_by.return_value = sales_qs
        sales_qs.filter.return_value = [sale]
        payments_qs = MagicMock()
        payments_qs.order_by.return_value = payments_qs
        payments_qs.filter.return_value = []
        returns_qs = MagicMock()
        returns_qs.order_by.return_value = returns_qs
        returns_qs.filter.return_value = []
        advance_entries_qs = MagicMock()
        advance_entries_qs.order_by.return_value = advance_entries_qs
        advance_entries_qs.filter.return_value = []

        with patch.object(ledger_views.CustomerMaster.objects, 'all', return_value=customer_qs), \
             patch.object(ledger_views, 'get_object_or_404', return_value=customer), \
             patch.object(ledger_views.SalesInvoiceMaster.objects, 'filter', return_value=sales_qs), \
             patch.object(ledger_views.SalesInvoicePaid.objects, 'filter', return_value=payments_qs), \
             patch.object(ledger_views.ReturnSalesInvoiceMaster.objects, 'filter', return_value=returns_qs), \
             patch.object(ledger_views.AdvanceLedger.objects, 'filter', return_value=advance_entries_qs), \
             patch.object(ledger_views, '_customer_opening_balance', return_value=145), \
             patch.object(ledger_views.Pharmacy_Details.objects, 'first', return_value=None), \
             patch.object(ledger_views, 'render', return_value=object()) as render:
            ledger_views.customer_ledger.__wrapped__(request, customer_id=1)

        context = render.call_args.args[2]
        self.assertEqual(context['start_date'], '2024-04-01')
        self.assertEqual(context['end_date'], '2025-03-31')
        self.assertEqual(len(context['transactions']), 1)
        self.assertEqual(context['transactions'][0]['type'], 'Sales Invoice')
        self.assertEqual(context['transactions'][0]['reference'], 'SI-UNPAID')
        self.assertEqual(context['opening_balance'], 145)
        self.assertEqual(context['transactions'][0]['balance'], 820)
        self.assertEqual(context['closing_balance'], 820)
        self.assertEqual(context['total_debit'], 675)


class SupplierLedgerPurchaseTests(SimpleTestCase):
    def test_unpaid_supplier_invoice_appears_in_selected_financial_year(self):
        request = RequestFactory().get('/ledger/supplier/1/')
        request.session = {'selected_year': 2024}
        request.user = MagicMock(is_authenticated=True)
        supplier = MagicMock(supplier_name='Test Supplier')
        purchase = MagicMock(
            invoice_date=date(2024, 6, 1),
            invoice_no='PI-UNPAID',
            invoice_total=825,
        )

        supplier_qs = MagicMock()
        supplier_qs.order_by.return_value = []
        purchases_qs = MagicMock()
        purchases_qs.order_by.return_value = purchases_qs
        purchases_qs.filter.return_value = [purchase]
        payments_qs = MagicMock()
        payments_qs.order_by.return_value = payments_qs
        payments_qs.filter.return_value = []
        returns_qs = MagicMock()
        returns_qs.order_by.return_value = returns_qs
        returns_qs.filter.return_value = []
        advance_entries_qs = MagicMock()
        advance_entries_qs.order_by.return_value = advance_entries_qs
        advance_entries_qs.filter.return_value = []
        advances_qs = MagicMock()
        advances_qs.__iter__ = lambda self: iter([])

        with patch.object(ledger_views.SupplierMaster.objects, 'all', return_value=supplier_qs), \
             patch.object(ledger_views, 'get_object_or_404', return_value=supplier), \
             patch.object(ledger_views.InvoiceMaster.objects, 'filter', return_value=purchases_qs), \
             patch.object(ledger_views.InvoicePaid.objects, 'filter', return_value=payments_qs), \
             patch.object(ledger_views.ReturnInvoiceMaster.objects, 'filter', return_value=returns_qs), \
             patch.object(ledger_views.AdvanceLedger.objects, 'filter', return_value=advance_entries_qs), \
             patch.object(ledger_views.SupplierAdvance.objects, 'filter', return_value=advances_qs), \
             patch.object(ledger_views, '_supplier_opening_balance', return_value=100), \
             patch.object(ledger_views.Pharmacy_Details.objects, 'first', return_value=None), \
             patch.object(ledger_views, 'render', return_value=object()) as render:
            ledger_views.supplier_ledger.__wrapped__(request, supplier_id=1)

        context = render.call_args.args[2]
        self.assertEqual(context['start_date'], '2024-04-01')
        self.assertEqual(context['end_date'], '2025-03-31')
        self.assertEqual(len(context['transactions']), 1)
        self.assertEqual(context['transactions'][0]['type'], 'Purchase Invoice')
        self.assertEqual(context['transactions'][0]['reference'], 'PI-UNPAID')
        self.assertEqual(context['opening_balance'], 100)
        self.assertEqual(context['transactions'][0]['balance'], 925)
        self.assertEqual(context['closing_balance'], 925)
        self.assertEqual(context['total_credit'], 825)


class LedgerOpeningBalanceCalculationTests(SimpleTestCase):
    def test_customer_opening_balance_includes_prior_sales_payments_returns_and_advances_once(self):
        with patch.object(ledger_views, '_sum_before', side_effect=[1000, 250, 50, 100]):
            opening_balance = ledger_views._customer_opening_balance(
                MagicMock(), '2024-04-01'
            )

        self.assertEqual(opening_balance, 600)

    def test_supplier_opening_balance_includes_prior_purchases_payments_returns_and_advances_once(self):
        with patch.object(ledger_views, '_sum_before', side_effect=[1000, 250, 50, 100]):
            opening_balance = ledger_views._supplier_opening_balance(
                MagicMock(), '2024-04-01'
            )

        self.assertEqual(opening_balance, 600)


class PurchaseInvoiceFinancialYearTests(SimpleTestCase):
    def test_credit_invoice_does_not_record_payment_or_use_submitted_amount(self):
        request = RequestFactory().post(
            '/invoices/add-with-products/',
            {
                'invoice_date': '2026-06-01',
                'products_data': '[]',
                'initial_payment_mode': 'Credit',
                'initial_payment_amount': '40.50',
            },
        )
        request.session = {'selected_year': 2026}
        request.user = MagicMock(is_authenticated=True)
        invoice = MagicMock(
            invoiceid=12,
            invoice_no='PUR-100',
            invoice_date=date(2026, 6, 1),
            invoice_total=100,
            invoice_paid=0,
        )

        class FormStub:
            cleaned_data = {'invoice_date': date(2026, 6, 1)}
            errors = {}

            def is_valid(self):
                return True

            def save(self, commit=False):
                return invoice

        with patch.object(combined_invoice_view, 'InvoiceForm', return_value=FormStub()), \
             patch.object(combined_invoice_view.transaction, 'atomic', return_value=nullcontext()), \
             patch.object(combined_invoice_view.InvoicePaid.objects, 'create') as create_payment, \
             patch.object(combined_invoice_view, '_auto_adjust_advance', return_value='') as adjust_advance, \
             patch.object(combined_invoice_view, 'redirect', return_value=object()), \
             patch.object(combined_invoice_view.messages, 'info'), \
             patch.object(combined_invoice_view.messages, 'success'):
            combined_invoice_view.add_invoice_with_products.__wrapped__(request)

        create_payment.assert_not_called()
        adjust_advance.assert_not_called()

    def test_cash_invoice_records_full_invoice_total_from_form(self):
        request = RequestFactory().post(
            '/invoices/add-with-products/',
            {
                'invoice_date': '2026-06-01',
                'products_data': '[]',
                'initial_payment_mode': 'Cash',
                'initial_payment_amount': '40.50',
            },
        )
        request.session = {'selected_year': 2026}
        request.user = MagicMock(is_authenticated=True)
        invoice = MagicMock(
            invoiceid=12,
            invoice_no='PUR-100',
            invoice_date=date(2026, 6, 1),
            invoice_total=100,
            invoice_paid=0,
        )

        class FormStub:
            cleaned_data = {'invoice_date': date(2026, 6, 1)}
            errors = {}

            def is_valid(self):
                return True

            def save(self, commit=False):
                return invoice

        with patch.object(combined_invoice_view, 'InvoiceForm', return_value=FormStub()), \
             patch.object(combined_invoice_view.transaction, 'atomic', return_value=nullcontext()), \
             patch.object(combined_invoice_view.InvoicePaid.objects, 'create') as create_payment, \
             patch.object(combined_invoice_view, 'redirect', return_value=object()), \
             patch.object(combined_invoice_view.messages, 'info'), \
             patch.object(combined_invoice_view.messages, 'success'):
            combined_invoice_view.add_invoice_with_products.__wrapped__(request)

        create_payment.assert_called_once_with(
            ip_invoiceid=invoice,
            payment_date=date(2026, 6, 1),
            payment_amount=100.0,
            payment_mode='Cash',
            payment_ref_no='',
        )

    def test_cash_invoice_records_full_invoice_total(self):
        invoice = MagicMock(
            invoice_total=100,
            invoice_paid=0,
            invoice_date=date(2026, 6, 1),
            invoice_no='PUR-100',
        )
        with patch.object(combined_invoice_view.InvoicePaid.objects, 'create') as create_payment:
            applied_amount, excess_amount = combined_invoice_view._record_initial_supplier_payment(
                invoice,
                'Cash',
            )

        self.assertEqual(applied_amount, Decimal('100.00'))
        self.assertEqual(excess_amount, Decimal('0.00'))
        create_payment.assert_called_once_with(
            ip_invoiceid=invoice,
            payment_date=date(2026, 6, 1),
            payment_amount=100.0,
            payment_mode='Cash',
            payment_ref_no='',
        )

    def test_credit_supplier_invoice_does_not_create_payment(self):
        invoice = MagicMock(
            invoice_total=100,
            invoice_paid=0,
            invoice_date=date(2026, 6, 1),
            invoice_no='PUR-100',
        )
        with patch.object(combined_invoice_view.InvoicePaid.objects, 'create') as create_payment, \
             patch.object(combined_invoice_view.SupplierAdvance.objects, 'create') as create_advance, \
             patch.object(combined_invoice_view.AdvanceLedger.objects, 'create') as create_ledger:
            applied_amount, excess_amount = combined_invoice_view._record_initial_supplier_payment(
                invoice,
                'Credit',
            )

        self.assertEqual(applied_amount, Decimal('0.00'))
        self.assertEqual(excess_amount, Decimal('0.00'))
        create_payment.assert_not_called()
        create_advance.assert_not_called()
        create_ledger.assert_not_called()

    def test_financial_year_starts_in_april_and_changes_in_march(self):
        self.assertEqual(get_financial_year_start(date(2012, 4, 1)), 2012)
        self.assertEqual(get_financial_year_start(date(2013, 3, 31)), 2012)
        self.assertEqual(get_financial_year_start(date(2013, 4, 1)), 2013)

    def test_financial_year_label_is_readable(self):
        self.assertEqual(get_financial_year_label(date(2026, 4, 1)), '2026-27')
        self.assertEqual(get_financial_year_label(date(2026, 3, 31)), '2025-26')

    def test_invoice_save_sets_financial_year_and_updates_it_with_invoice_date(self):
        invoice = models.InvoiceMaster(invoice_date=date(2013, 4, 1))

        with patch.object(models.models.Model, 'save') as save_model:
            invoice.save(update_fields=['invoice_date'])

        self.assertEqual(invoice.invoice_financial_year, '2013-14')
        self.assertEqual(
            save_model.call_args.kwargs['update_fields'],
            {'invoice_date', 'invoice_financial_year'},
        )

    def test_invoice_form_rejects_duplicate_number_within_supplier_fy(self):
        supplier = MagicMock()
        supplier.pk = 101
        form = InvoiceForm()
        form._errors = ErrorDict()
        form.cleaned_data = {
            'invoice_no': '101',
            'supplierid': supplier,
            'invoice_date': date(2013, 3, 31),
        }
        existing_invoices = MagicMock()
        existing_invoices.exists.return_value = True

        with patch.object(
            models.InvoiceMaster.objects,
            'filter',
            return_value=existing_invoices,
        ) as filter_invoices:
            form.clean()

        filter_invoices.assert_called_once_with(
            invoice_no='101',
            supplierid=supplier,
            invoice_financial_year='2012-13',
        )
        self.assertIn('invoice_no', form.errors)

    def test_invoice_form_allows_duplicate_number_in_another_fy(self):
        supplier = MagicMock()
        supplier.pk = 101
        form = InvoiceForm()
        form._errors = ErrorDict()
        form.cleaned_data = {
            'invoice_no': '101',
            'supplierid': supplier,
            'invoice_date': date(2013, 4, 1),
        }
        existing_invoices = MagicMock()
        existing_invoices.exists.return_value = False

        with patch.object(
            models.InvoiceMaster.objects,
            'filter',
            return_value=existing_invoices,
        ) as filter_invoices:
            form.clean()

        filter_invoices.assert_called_once_with(
            invoice_no='101',
            supplierid=supplier,
            invoice_financial_year='2013-14',
        )
        self.assertNotIn('invoice_no', form.errors)


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

    def test_reorder_report_keeps_only_batches_purchased_and_sold_in_selected_fy(self):
        purchase_batches = {
            101: {('B-SOLD', '08-2026'), ('B-UNSOLD', '08-2026')},
            202: {('B-NOT-PURCHASED', '08-2026')},
        }
        sales_by_batch = {
            (101, 'B-SOLD', '08-2026'): 5.0,
            (101, 'B-UNSOLD', '08-2026'): 0.0,
            (202, 'B-NOT-PURCHASED', '08-2026'): 3.0,
        }

        qualifying_batches, qualifying_sales = (
            reorder_level_views._financial_year_purchased_and_sold_batches(
                purchase_batches, sales_by_batch
            )
        )

        self.assertEqual(qualifying_batches, {101: {('B-SOLD', '08-2026')}})
        self.assertEqual(qualifying_sales, {(101, 'B-SOLD', '08-2026'): 5.0})

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
        request = RequestFactory().get('/reports/reorder-level/', {'financial_year': '2022'})
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

        self.assertEqual(mock_stats.call_args[0][2], date(2022, 4, 1))
        self.assertEqual(mock_stats.call_args[0][3], date(2023, 3, 31))
        self.assertEqual(request.session['selected_year'], 2022)


class CombinedSalesInvoiceDateTests(SimpleTestCase):
    def test_credit_sales_invoice_does_not_record_payment_or_use_submitted_amount(self):
        request = RequestFactory().post(
            '/sales/add-with-products/',
            {
                'sales_invoice_date': '2026-06-01',
                'products_data': '[]',
                'initial_payment_mode': 'credit',
                'initial_payment_amount': '40.50',
            },
        )
        request.session = {'selected_year': 2026}
        request.user = MagicMock(is_authenticated=True)

        customer = MagicMock(customer_type='TYPE-A')
        invoice = MagicMock(
            sales_invoice_no='INV-TEST',
            sales_invoice_date=date(2026, 6, 1),
            sales_invoice_total=100,
            sales_invoice_paid=0,
            customerid=customer,
        )

        class FormStub:
            cleaned_data = {'sales_invoice_date': date(2026, 6, 1)}
            errors = {}

            def is_valid(self):
                return True

            def save(self, commit=False):
                return invoice

        with patch.object(views, 'SalesInvoiceForm', return_value=FormStub()), \
             patch.object(views, 'generate_sales_invoice_number', return_value='INV-TEST'), \
             patch.object(views.SalesInvoicePaid.objects, 'create') as create_payment, \
             patch.object(views.transaction, 'atomic', return_value=nullcontext()), \
             patch.object(views, '_auto_adjust_customer_advance', return_value='') as adjust_advance, \
             patch.object(views, 'redirect', return_value=object()), \
             patch.object(views.messages, 'info'), \
             patch.object(views.messages, 'success'):
            views.add_sales_invoice_with_products.__wrapped__(request)

        create_payment.assert_not_called()
        adjust_advance.assert_not_called()

    def test_cash_sales_invoice_records_full_invoice_total(self):
        request = RequestFactory().post(
            '/sales/add-with-products/',
            {
                'sales_invoice_date': '2026-06-01',
                'products_data': '[]',
                'initial_payment_mode': 'cash',
                'initial_payment_amount': '40.50',
            },
        )
        request.session = {'selected_year': 2026}
        request.user = MagicMock(is_authenticated=True)

        customer = MagicMock(customer_type='TYPE-A')
        invoice = MagicMock(
            sales_invoice_no='INV-TEST',
            sales_invoice_date=date(2026, 6, 1),
            sales_invoice_total=100,
            sales_invoice_paid=0,
            customerid=customer,
        )

        class FormStub:
            cleaned_data = {'sales_invoice_date': date(2026, 6, 1)}
            errors = {}

            def is_valid(self):
                return True

            def save(self, commit=False):
                return invoice

        with patch.object(views, 'SalesInvoiceForm', return_value=FormStub()), \
             patch.object(views, 'generate_sales_invoice_number', return_value='INV-TEST'), \
             patch.object(views.SalesInvoicePaid.objects, 'create') as create_payment, \
             patch.object(views.transaction, 'atomic', return_value=nullcontext()), \
             patch.object(views, '_auto_adjust_customer_advance', return_value=''), \
             patch.object(views, 'redirect', return_value=object()), \
             patch.object(views.messages, 'info'), \
             patch.object(views.messages, 'success'):
            views.add_sales_invoice_with_products.__wrapped__(request)

        create_payment.assert_called_once_with(
            sales_ip_invoice_no=invoice,
            sales_payment_date=date(2026, 6, 1),
            sales_payment_amount=100.0,
            sales_payment_mode='Cash',
            sales_payment_ref_no='',
        )

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
