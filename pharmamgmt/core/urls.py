from django.urls import path, include
from . import views
from .product_api import add_product_api
from .gst_invoice_view import print_gst_purchase_invoice, print_gst_sales_invoice, print_gst_purchase_return_invoice, print_gst_sales_return_invoice
from .challan_views import (
    supplier_challan_list, add_supplier_challan, view_supplier_challan, delete_supplier_challan,
    customer_challan_list, add_customer_challan, view_customer_challan, delete_customer_challan,
    get_next_challan_number, add_challan_series,
    create_customer_invoice_from_challans, get_customer_challans_api, get_challan_products_api
)
from .combined_invoice_view import add_invoice_with_products, get_existing_batches, cleanup_duplicate_batches, get_supplier_challans, get_challan_products
from .low_stock_views import low_stock_update, update_low_stock_item, bulk_update_low_stock, get_batch_suggestions
from .bulk_upload_views import bulk_upload_products, download_product_template
from core.bulk_upload_view import bulk_upload_invoices
from .ledger_views import customer_ledger, supplier_ledger, ledger_selection, customer_ledger_print, supplier_ledger_print, export_supplier_ledger_pdf, export_supplier_ledger_excel, export_customer_ledger_pdf, export_customer_ledger_excel
from .sales2_views import sales2_report, sales2_report_pdf, sales2_report_excel
from .purchase2_views import purchase2_report, purchase2_report_pdf, purchase2_report_excel
from .customer_sales_views import customer_wise_sales_report, quick_customer_search, customer_sales_summary
from .stock_report_views import stock_statement_report, stock_statement_batch_detail, export_stock_statement_pdf
from .balance_check_view import check_invoice_balance, fix_small_balance
from .stock_issue_views import (
    stock_issue_list, add_stock_issue, stock_issue_detail, delete_stock_issue,
    get_product_batch_info, search_products_for_issue
)
from .inventory_export_views import (
    export_batch_inventory_pdf, export_batch_inventory_excel,
    export_dateexpiry_inventory_pdf, export_dateexpiry_inventory_excel
)
from .financial_views import financial_report, export_financial_pdf, export_financial_excel
from .backup_views import backup_list, create_backup, restore_backup, download_backup, delete_backup
from .return_receipt_views import print_purchase_return_receipt, print_sales_return_receipt
from .cached_inventory_views import inventory_list_cached
# ============================================
# CONTRA ENTRY MODULE - IMPORTS
# ============================================
from .contra_views import contra_list, add_contra, edit_contra, delete_contra, contra_detail
# ============================================

from .year_filter_views import set_year_filter

urlpatterns = [
    # Landing Page (Root URL)
    path('', views.landing_page, name='landing_page'),
    # path('landing2', views.landing2_page, name='landing2_page'),
    # path('landing3', views.landing3_page, name='landing3_page'),
    
    # Year Filter
    path('set-year-filter/', set_year_filter, name='set_year_filter'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # User management
    path('register/', views.register_user, name='register'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:pk>/update/', views.update_user, name='update_user'),
    path('users/<int:pk>/delete/', views.delete_user, name='delete_user'),
    path('profile/', views.profile, name='profile'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Pharmacy details
    path('pharmacy-details/', views.pharmacy_details, name='pharmacy_details'),
    
    # Products
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/bulk-upload/', bulk_upload_products, name='bulk_upload_products'),
    path('products/download-template/', download_product_template, name='download_product_template'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/update/', views.update_product, name='update_product'),
    path('products/<int:pk>/delete/', views.delete_product, name='delete_product'),
    
    # Backup Management (MOVED BEFORE SUPPLIERS TO AVOID CONFLICT)
    path('system/backups/', backup_list, name='backup_list'),
    path('system/backups/create/', create_backup, name='create_backup'),
    path('system/backups/restore/', restore_backup, name='restore_backup'),
    path('system/backups/download/<str:filename>/', download_backup, name='download_backup'),
    path('system/backups/delete/', delete_backup, name='delete_backup'),
    path('download-backup-logout/<str:filename>/', views.download_backup_and_logout, name='download_backup_and_logout'),
    
    # Suppliers
    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.add_supplier, name='add_supplier'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:pk>/update/', views.update_supplier, name='update_supplier'),
    path('suppliers/<int:pk>/delete/', views.delete_supplier, name='delete_supplier'),
    path('api/search-suppliers/', views.search_suppliers_api, name='search_suppliers_api'),
    
    # Customers
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/add/', views.add_customer, name='add_customer'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/update/', views.update_customer, name='update_customer'),
    path('customers/<int:pk>/delete/', views.delete_customer, name='delete_customer'),
    path('api/search-customers/', views.search_customers_api, name='search_customers_api'),
    
    # Challan
    path('challan/supplier/', supplier_challan_list, name='supplier_challan_list'),
    path('challan/supplier/add/', add_supplier_challan, name='add_supplier_challan'),
    path('challan/supplier/<int:challan_id>/', view_supplier_challan, name='view_supplier_challan'),
    path('delete-supplier-challan/<int:challan_id>/', delete_supplier_challan, name='delete_supplier_challan'),
    path('challan/customer/', customer_challan_list, name='customer_challan_list'),
    path('challan/customer/add/', add_customer_challan, name='add_customer_challan'),
    path('challan/customer/<int:challan_id>/', view_customer_challan, name='view_customer_challan'),
    path('delete-customer-challan/<int:challan_id>/', delete_customer_challan, name='delete_customer_challan'),
    path('api/get-next-challan-number/', get_next_challan_number, name='get_next_challan_number'),
    path('api/add-challan-series/', add_challan_series, name='add_challan_series'),
    path('api/create-invoice-from-challans/', create_customer_invoice_from_challans, name='create_customer_invoice_from_challans'),
    path('api/customer-challans/', get_customer_challans_api, name='get_customer_challans_api'),
    path('api/get-challan-products/', get_challan_products_api, name='get_challan_products_api'),
    
    # Purchase Invoices
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/add/', views.add_invoice, name='add_invoice'),
    path('invoices/add-with-products/', views.add_invoice_with_products, name='add_invoice_with_products'),

    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),

    path('invoices/<int:pk>/edit/', views.edit_invoice, name='edit_invoice'),
    path('invoices/<int:pk>/delete/', views.delete_invoice, name='delete_invoice'),
    path('invoices/<int:invoice_id>/add-purchase/', views.add_purchase, name='add_purchase'),
    path('invoices/<int:invoice_id>/edit-purchase/<int:purchase_id>/', views.edit_purchase, name='edit_purchase'),
    path('invoices/<int:invoice_id>/delete-purchase/<int:purchase_id>/', views.delete_purchase, name='delete_purchase'),
    path('invoices/<int:invoice_id>/add-payment/', views.add_invoice_payment, name='add_invoice_payment'),
    path('invoices/<int:invoice_id>/edit-payment/<int:payment_id>/', views.edit_invoice_payment, name='edit_invoice_payment'),
    path('invoices/<int:invoice_id>/delete-payment/<int:payment_id>/', views.delete_invoice_payment, name='delete_invoice_payment'),

    
    # Sales Receipt
    path('sales/<str:invoice_id>/print-receipt/', views.print_sales_receipt, name='print_sales_receipt'),
    path('sales/<str:invoice_id>/gst-invoice/', print_gst_sales_invoice, name='print_gst_sales_invoice'),
    
    # Purchase Receipt
    path('purchases/<int:invoice_id>/print-receipt/', views.print_purchase_receipt, name='print_purchase_receipt'),
    path('purchases/<int:invoice_id>/gst-invoice/', print_gst_purchase_invoice, name='print_gst_purchase_invoice'),
    
    # Purchase Return Receipt
    path('purchase-returns/<str:return_id>/print-receipt/', print_purchase_return_receipt, name='print_purchase_return_receipt'),
    path('purchase-returns/<str:return_id>/gst-invoice/', print_gst_purchase_return_invoice, name='print_gst_purchase_return_invoice'),
    
    # Sales Return Receipt
    path('sales-returns/<str:return_id>/print-receipt/', print_sales_return_receipt, name='print_sales_return_receipt'),
    path('sales-returns/<str:return_id>/gst-invoice/', print_gst_sales_return_invoice, name='print_gst_sales_return_invoice'),
    
    # Sales Invoices
    path('sales/', views.sales_invoice_list, name='sales_invoice_list'),

    path('sales/add/', views.add_sales_invoice, name='add_sales_invoice'),
    path('sales/add-with-products/', views.add_sales_invoice_with_products, name='add_sales_invoice_with_products'),
    path('sales/<str:pk>/', views.sales_invoice_detail, name='sales_invoice_detail'),
    path('sales/<str:pk>/edit/', views.edit_sales_invoice, name='edit_sales_invoice'),

    path('sales/<str:pk>/delete/', views.delete_sales_invoice, name='delete_sales_invoice'),
    path('sales/<str:invoice_id>/add-sale/', views.add_sale, name='add_sale'),
    path('sales/<str:invoice_id>/edit-sale/<int:sale_id>/', views.edit_sale, name='edit_sale'),
    path('sales/<str:invoice_id>/delete-sale/<int:sale_id>/', views.delete_sale, name='delete_sale'),
    path('sales/<str:invoice_id>/add-payment/', views.add_sales_payment, name='add_sales_payment'),
    path('sales/<str:invoice_id>/edit-payment/<int:payment_id>/', views.edit_sales_payment, name='edit_sales_payment'),
    path('sales/<str:invoice_id>/delete-payment/<int:payment_id>/', views.delete_sales_payment, name='delete_sales_payment'),
    
    # Purchase Returns
    path('purchase-returns/', views.purchase_return_list, name='purchase_return_list'),
    path('purchase-returns/add/', views.add_purchase_return, name='add_purchase_return'),
    path('purchase-returns/<str:pk>/', views.purchase_return_detail, name='purchase_return_detail'),
    path('purchase-returns/<str:pk>/edit/', views.edit_purchase_return, name='edit_purchase_return'),
    path('purchase-returns/<str:pk>/delete/', views.delete_purchase_return, name='delete_purchase_return'),
    path('purchase-returns/<str:return_id>/add-item/', views.add_purchase_return_item, name='add_purchase_return_item'),
    path('purchase-returns/<str:return_id>/edit-item/<int:item_id>/', views.edit_purchase_return_item, name='edit_purchase_return_item'),
    path('purchase-returns/<str:return_id>/delete-item/<int:item_id>/', views.delete_purchase_return_item, name='delete_purchase_return_item'),
    
    # Sales Returns
    path('sales-returns/', views.sales_return_list, name='sales_return_list'),
    path('sales-returns/add/', views.add_sales_return, name='add_sales_return'),
    path('sales-returns/<str:pk>/', views.sales_return_detail, name='sales_return_detail'),
    path('sales-returns/<str:pk>/delete/', views.delete_sales_return, name='delete_sales_return'),
    path('sales-returns/<str:return_id>/add-item/', views.add_sales_return_item, name='add_sales_return_item'),
    path('sales-returns/<str:return_id>/edit-item/<int:item_id>/', views.edit_sales_return_item, name='edit_sales_return_item'),
    path('sales-returns/<str:return_id>/delete-item/<int:item_id>/', views.delete_sales_return_item, name='delete_sales_return_item'),
    path('sales-returns/<str:return_id>/add-payment/', views.add_sales_return_payment, name='add_sales_return_payment'),
    path('sales-returns/<str:return_id>/edit-payment/<int:payment_id>/', views.edit_sales_return_payment, name='edit_sales_return_payment'),
    path('sales-returns/<str:return_id>/delete-payment/<int:payment_id>/', views.delete_sales_return_payment, name='delete_sales_return_payment'),
    
    # Sales Return API endpoints
    path('api/sales-invoices-for-customer/', views.get_sales_invoices_for_customer, name='get_sales_invoices_for_customer'),
    path('api/sales-invoice-items/', views.get_sales_invoice_items, name='get_sales_invoice_items'),
    
    # Invoice Series URLs
    path('api/add-invoice-series/', views.add_invoice_series, name='add_invoice_series'),
    path('api/get-invoice-series/', views.get_invoice_series, name='get_invoice_series'),
    path('api/get-next-invoice-number/', views.get_next_invoice_number, name='get_next_invoice_number'),
    path('api/product-search-suggestions/', views.product_search_suggestions, name='product_search_suggestions'),
    path('api/delete-invoice-series/<int:series_id>/', views.delete_invoice_series, name='delete_invoice_series'),
 
    # Inventory (Cache will auto-populate via signals)
    path('inventory/', inventory_list_cached, name='inventory_list'),
    path('api/inventory-search-suggestions/', views.inventory_search_suggestions, name='inventory_search_suggestions'),
    
    # Reports
    path('reports/inventory/batch/', views.batch_inventory_report, name='batch_inventory_report'),
    path('reports/inventory/expiry/', views.dateexpiry_inventory_report, name='dateexpiry_inventory_report'),
    path('reports/stock-statement/', stock_statement_report, name='stock_statement_report'),
    path('reports/stock-statement/batch-details/<int:product_id>/', stock_statement_batch_detail, name='stock_statement_batch_detail'),
    path('reports/stock-statement/pdf/', export_stock_statement_pdf, name='export_stock_statement_pdf'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/sales2/', sales2_report, name='sales2_report'),
    path('reports/sales2/pdf/', sales2_report_pdf, name='sales2_report_pdf'),
    path('reports/sales2/excel/', sales2_report_excel, name='sales2_report_excel'),
    path('reports/purchases/', views.purchase_report, name='purchase_report'),
    path('reports/purchase2/', purchase2_report, name='purchase2_report'),
    path('reports/purchase2/pdf/', purchase2_report_pdf, name='purchase2_report_pdf'),
    path('reports/purchase2/excel/', purchase2_report_excel, name='purchase2_report_excel'),
    path('reports/financial/', financial_report, name='financial_report'),
    path('reports/financial/pdf/', export_financial_pdf, name='export_financial_pdf'),
    path('reports/financial/excel/', export_financial_excel, name='export_financial_excel'),

    
    # Customer Sales Reports
    path('reports/customer-sales/', customer_wise_sales_report, name='customer_wise_sales_report'),
    path('api/quick-customer-search/', quick_customer_search, name='quick_customer_search'),
    path('api/customer-sales-summary/<int:customer_id>/', customer_sales_summary, name='customer_sales_summary'),
    
    # API endpoints for AJAX calls
    path('get-product-info/', views.get_product_info, name='get_product_info'),
    path('api/product-info/', views.get_product_info, name='get_product_info_api'),
    path('api/product-by-barcode/', views.get_product_by_barcode, name='get_product_by_barcode'),
    path('api/export-inventory/', views.export_inventory_csv, name='export_inventory_csv'),

    
    # Export URLs
    path('export/inventory/pdf/', views.export_inventory_pdf, name='export_inventory_pdf'),
    path('export/inventory/excel/', views.export_inventory_excel, name='export_inventory_excel'),
    
    # Enhanced Inventory Export URLs
    path('export/batch-inventory/pdf/', export_batch_inventory_pdf, name='export_batch_inventory_pdf'),
    path('export/batch-inventory/excel/', export_batch_inventory_excel, name='export_batch_inventory_excel'),
    path('export/dateexpiry-inventory/pdf/', export_dateexpiry_inventory_pdf, name='export_dateexpiry_inventory_pdf'),
    path('export/dateexpiry-inventory/excel/', export_dateexpiry_inventory_excel, name='export_dateexpiry_inventory_excel'),
    path('export/sales/pdf/', views.export_sales_pdf, name='export_sales_pdf'),
    path('export/sales/excel/', views.export_sales_excel, name='export_sales_excel'),
    path('export/purchases/pdf/', views.export_purchases_pdf, name='export_purchases_pdf'),
    # path('export/purchases/excel/', views.export_purchases_excel, name='export/financial/pdf/', views.export_financial_pdf, name='export_financial_pdf'),
    path('export/purchases/excel/', views.export_purchases_excel, name='export_purchases_excel'),

    
    # Sale Rate Management
    path('rates/', views.sale_rate_list, name='sale_rate_list'),
    path('rates/add/', views.add_sale_rate, name='add_sale_rate'),
    path('rates/<int:pk>/update/', views.update_sale_rate, name='update_sale_rate'),
    path('rates/<int:pk>/delete/', views.delete_sale_rate, name='delete_sale_rate'),
    
    # API endpoints for batch functionality
    path('api/product-batches/', views.get_product_batches, name='get_product_batches'),
    path('api/batch-details/', views.get_batch_details, name='get_batch_details'),
    path('api/product-batch-selector/', views.get_product_batch_selector, name='api_product_batch_selector'),
    path('api/search-products/', views.search_products_api, name='search_products_api'),
    path('api/customer-rate-info/', views.get_customer_rate_info, name='api_customer_rate_info'),
    path('api/get-batch-rates/', views.get_batch_rates, name='get_batch_rates'),
    path('api/update-purchase-return/', views.update_purchase_return_api, name='update_purchase_return_api'),
    path('api/update-sales-return/', views.update_sales_return_api, name='update_sales_return_api'),
    path('api/delete-sales-return-item/', views.delete_sales_return_item_api, name='delete_sales_return_item_api'),
    
    # Stock Management APIs
    path('api/existing-batches/', get_existing_batches, name='get_existing_batches'),
    path('api/cleanup-duplicate-batches/', cleanup_duplicate_batches, name='cleanup_duplicate_batches'),
    path('api/supplier-challans/', get_supplier_challans, name='get_supplier_challans'),
    path('api/challan-products/', get_challan_products, name='get_challan_products'),
    
    # Low Stock Update
    path('inventory/low-stock-update/', low_stock_update, name='low_stock_update'),
    path('api/update-low-stock-item/', update_low_stock_item, name='update_low_stock_item'),
    path('api/bulk-update-low-stock/', bulk_update_low_stock, name='bulk_update_low_stock'),
    path('get-batch-suggestions/', get_batch_suggestions, name='get_batch_suggestions'),
    
    # Stock Issues
    path('stock-issues/', stock_issue_list, name='stock_issue_list'),
    path('stock-issues/add/', add_stock_issue, name='add_stock_issue'),
    path('stock-issues/<int:pk>/', stock_issue_detail, name='stock_issue_detail'),
    path('stock-issues/<int:pk>/delete/', delete_stock_issue, name='delete_stock_issue'),
    path('stock-issues/api/product-batch-info/', get_product_batch_info, name='get_product_batch_info_stock'),
    path('stock-issues/api/search-products/', search_products_for_issue, name='search_products_for_issue'),
    

    
    # Finance - Payments
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/add/', views.add_payment, name='add_payment'),
    path('payments/<int:pk>/edit/', views.edit_payment, name='edit_payment'),
    path('payments/<int:pk>/delete/', views.delete_payment, name='delete_payment'),
    path('payments/export-pdf/', views.export_payments_pdf, name='export_payments_pdf'),
    path('payments/export-excel/', views.export_payments_excel, name='export_payments_excel'),
    path('api/search-supplier-invoices/', views.search_supplier_invoices, name='search_supplier_invoices'),
    path('api/search-customer-invoices/', views.search_customer_invoices, name='search_customer_invoices'),
    
    # Unified Payment/Receipt Form
    path('finance/add/', views.add_unified_payment, name='add_unified_payment'),
    path('unified-payment/', views.add_unified_payment, name='unified_payment'),
    
    # Balance Check APIs
    path('api/check-invoice-balance/', check_invoice_balance, name='check_invoice_balance'),
    path('api/fix-small-balance/', fix_small_balance, name='fix_small_balance'),
    
    # Finance - Receipts
    path('receipts/', include('core.receipt_urls')),
    
    # Ledger
    path('ledger/', ledger_selection, name='ledger_selection'),
    path('ledger/customer/', customer_ledger, name='customer_ledger'),
    path('ledger/customer/<int:customer_id>/', customer_ledger, name='customer_ledger_detail'),
    path('ledger/customer/<int:customer_id>/print/', customer_ledger_print, name='customer_ledger_print'),
    path('ledger/supplier/', supplier_ledger, name='supplier_ledger'),
    path('ledger/supplier/<int:supplier_id>/', supplier_ledger, name='supplier_ledger_detail'),
    path('ledger/supplier/<int:supplier_id>/print/', supplier_ledger_print, name='supplier_ledger_print'),
    path('ledger/supplier/<int:supplier_id>/export-pdf/', export_supplier_ledger_pdf, name='export_supplier_ledger_pdf'),
    path('ledger/supplier/<int:supplier_id>/export-excel/', export_supplier_ledger_excel, name='export_supplier_ledger_excel'),
    path('ledger/customer/<int:customer_id>/export-pdf/', export_customer_ledger_pdf, name='export_customer_ledger_pdf'),
    path('ledger/customer/<int:customer_id>/export-excel/', export_customer_ledger_excel, name='export_customer_ledger_excel'),
    
    # API for supplier selection
    path('api/get-suppliers/', views.get_suppliers_api, name='get_suppliers_api'),
    
    # API for adding product from any form
    path('api/add-product/', add_product_api, name='add_product_api'),
    
    path('bulk-upload-invoices/', bulk_upload_invoices, name='bulk_upload_invoices'),
    path('api/get-suppliers-with-invoices/', views.get_suppliers_with_invoices, name='get_suppliers_with_invoices'),
    
    # ============================================
    # CONTRA ENTRY MODULE - URLS
    # ============================================
    path('contra/', contra_list, name='contra_list'),
    path('contra/add/', add_contra, name='add_contra'),
    path('contra/<int:contra_id>/', contra_detail, name='contra_detail'),
    path('contra/<int:contra_id>/edit/', edit_contra, name='edit_contra'),
    path('contra/<int:contra_id>/delete/', delete_contra, name='delete_contra'),
    # ====================
    # ========================
]


