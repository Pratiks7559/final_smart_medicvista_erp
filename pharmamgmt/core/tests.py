from datetime import date
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, SimpleTestCase

from core import reorder_level_views


class ReorderLevelReportTests(SimpleTestCase):
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
