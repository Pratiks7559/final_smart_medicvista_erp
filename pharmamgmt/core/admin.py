from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Web_User, Pharmacy_Details, ProductMaster, SupplierMaster, CustomerMaster,
    InvoiceMaster, InvoicePaid, PurchaseMaster, SalesInvoiceMaster, SalesMaster,
    SalesInvoicePaid, ProductRateMaster, ReturnInvoiceMaster, PurchaseReturnInvoicePaid,
    ReturnPurchaseMaster, ReturnSalesInvoiceMaster, ReturnSalesInvoicePaid, ReturnSalesMaster,
    Challan1, SupplierChallanMaster, SupplierChallanMaster2, CustomerChallan, CustomerChallanMaster, CustomerChallanMaster2, ChallanSeries,
    InvoiceSeries, StockIssueMaster, StockIssueDetail, ContraEntry
)

# Define custom admin classes

class Web_UserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'user_contact', 'path')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Custom Fields', {'fields': ('user_type', 'user_contact', 'path')}),
    )

class PharmacyDetailsAdmin(admin.ModelAdmin):
    list_display = ('pharmaname', 'proprietorname', 'proprietorcontact', 'proprietoremail')

class ProductMasterAdmin(admin.ModelAdmin):
    list_display = ('productid', 'product_name', 'product_company', 'product_packing', 'product_category', 'product_barcode')
    search_fields = ('product_name', 'product_company', 'product_salt', 'product_barcode')
    list_filter = ('product_category',)

class SupplierMasterAdmin(admin.ModelAdmin):
    list_display = ('supplierid', 'supplier_name', 'supplier_type', 'supplier_mobile', 'supplier_emailid')
    search_fields = ('supplier_name', 'supplier_mobile', 'supplier_emailid')

class CustomerMasterAdmin(admin.ModelAdmin):
    list_display = ('customerid', 'customer_name', 'customer_type', 'customer_mobile', 'customer_emailid')
    search_fields = ('customer_name', 'customer_mobile', 'customer_emailid')
    list_filter = ('customer_type',)

class InvoiceMasterAdmin(admin.ModelAdmin):
    list_display = ('invoiceid', 'invoice_no', 'invoice_date', 'supplierid', 'invoice_total', 'invoice_paid')
    list_filter = ('invoice_date',)
    search_fields = ('invoice_no', 'supplierid__supplier_name')

class PurchaseMasterAdmin(admin.ModelAdmin):
    list_display = ('purchaseid', 'product_name', 'product_company', 'product_batch_no', 
                    'product_quantity', 'product_expiry', 'total_amount')
    list_filter = ('purchase_entry_date', 'product_company')
    search_fields = ('product_name', 'product_batch_no', 'product_company')

class SalesInvoiceMasterAdmin(admin.ModelAdmin):
    list_display = ('sales_invoice_no', 'sales_invoice_date', 'customerid', 
                    'sales_invoice_total', 'sales_invoice_paid')
    list_filter = ('sales_invoice_date',)
    search_fields = ('sales_invoice_no', 'customerid__customer_name')

class SalesMasterAdmin(admin.ModelAdmin):
    list_display = ('id', 'sales_invoice_no', 'product_name', 'product_batch_no', 
                   'sale_quantity', 'sale_rate', 'sale_total_amount')
    list_filter = ('sale_entry_date',)
    search_fields = ('product_name', 'product_batch_no', 'sales_invoice_no__sales_invoice_no')



class InvoiceSeriesAdmin(admin.ModelAdmin):
    list_display = ('series_id', 'series_name', 'series_prefix', 'current_number', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('series_name',)



# Register models with admin site
admin.site.register(Web_User, Web_UserAdmin)
admin.site.register(Pharmacy_Details, PharmacyDetailsAdmin)
admin.site.register(ProductMaster, ProductMasterAdmin)
admin.site.register(SupplierMaster, SupplierMasterAdmin)
admin.site.register(CustomerMaster, CustomerMasterAdmin)
admin.site.register(InvoiceMaster, InvoiceMasterAdmin)
admin.site.register(InvoicePaid)
admin.site.register(PurchaseMaster, PurchaseMasterAdmin)
admin.site.register(SalesInvoiceMaster, SalesInvoiceMasterAdmin)
admin.site.register(SalesMaster, SalesMasterAdmin)
admin.site.register(SalesInvoicePaid)
admin.site.register(ProductRateMaster)
admin.site.register(ReturnInvoiceMaster)
admin.site.register(PurchaseReturnInvoicePaid)
admin.site.register(ReturnPurchaseMaster)
admin.site.register(ReturnSalesInvoiceMaster)
admin.site.register(ReturnSalesInvoicePaid)
admin.site.register(ReturnSalesMaster)
admin.site.register(Challan1)
admin.site.register(SupplierChallanMaster)
admin.site.register(SupplierChallanMaster2)
admin.site.register(CustomerChallan)
admin.site.register(CustomerChallanMaster)
admin.site.register(CustomerChallanMaster2)
admin.site.register(ChallanSeries)

admin.site.register(InvoiceSeries, InvoiceSeriesAdmin)


class InventoryMasterAdmin(admin.ModelAdmin):
    list_display = ('inventory_id', 'product', 'batch_no', 'current_stock', 'available_stock', 'expiry_date', 'is_active')
    list_filter = ('is_active', 'expiry_date', 'location')
    search_fields = ('product__product_name', 'batch_no')
    readonly_fields = ('available_stock', 'created_at', 'updated_at')

class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'inventory', 'transaction_type', 'quantity', 'transaction_date')
    list_filter = ('transaction_type', 'transaction_date')
    search_fields = ('inventory__product__product_name', 'inventory__batch_no')

class BatchStockSummaryAdmin(admin.ModelAdmin):
    list_display = ('summary_id', 'product', 'total_batches', 'total_stock', 'total_value', 'last_updated')
    readonly_fields = ('last_updated',)
    search_fields = ('product__product_name',)

class StockIssueMasterAdmin(admin.ModelAdmin):
    list_display = ('issue_id', 'issue_no', 'issue_date', 'issue_type', 'total_value', 'created_by')
    list_filter = ('issue_type', 'issue_date', 'created_by')
    search_fields = ('issue_no', 'remarks')
    readonly_fields = ('issue_no', 'created_at', 'updated_at')

class StockIssueDetailAdmin(admin.ModelAdmin):
    list_display = ('detail_id', 'issue', 'product', 'batch_no', 'quantity_issued', 'unit_rate', 'total_amount')
    list_filter = ('issue__issue_type', 'issue__issue_date')
    search_fields = ('product__product_name', 'batch_no', 'issue__issue_no')
    readonly_fields = ('total_amount',)

# REMOVED: Inventory models no longer needed
# admin.site.register(InventoryMaster, InventoryMasterAdmin)
# admin.site.register(InventoryTransaction, InventoryTransactionAdmin)
# admin.site.register(BatchStockSummary, BatchStockSummaryAdmin)
admin.site.register(StockIssueMaster, StockIssueMasterAdmin)
admin.site.register(StockIssueDetail, StockIssueDetailAdmin)

# ============================================
# CONTRA ENTRY MODULE - ADMIN
# ============================================
class ContraEntryAdmin(admin.ModelAdmin):
    list_display = ('contra_no', 'contra_date', 'contra_type', 'from_account', 'to_account', 'amount', 'created_by')
    list_filter = ('contra_type', 'contra_date', 'created_by')
    search_fields = ('contra_no', 'from_account', 'to_account', 'reference_no')
    readonly_fields = ('contra_no', 'created_at', 'updated_at')
    date_hierarchy = 'contra_date'

admin.site.register(ContraEntry, ContraEntryAdmin)
# ============================================

# ============================================
# RETAILER REPORT REQUEST MODULE - ADMIN
# ============================================
from .retailer_models import RetailerMaster, RetailerReportRequest

@admin.register(RetailerMaster)
class RetailerMasterAdmin(admin.ModelAdmin):
    list_display = ('retailer_id', 'retailer_name', 'retailer_code', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('retailer_name', 'retailer_code')
    readonly_fields = ('api_key', 'created_at')

@admin.register(RetailerReportRequest)
class RetailerReportRequestAdmin(admin.ModelAdmin):
    list_display = ('request_id', 'retailer', 'request_type', 'from_date', 'to_date', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'request_type', 'retailer')
    search_fields = ('retailer__retailer_name', 'created_by')
    readonly_fields = ('created_at',)
# ============================================
