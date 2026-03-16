from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from datetime import datetime
from decimal import Decimal
import csv
from django.http import HttpResponse
from django.db.models import Q, F 

# Create your models here.
class Web_User(AbstractUser):
    # firstname=models.CharField(max_length=150, null=False, blank=False )
    # lastname=models.CharField(max_length=150, null=False, blank=False)
    username=models.CharField(max_length=150, unique=True, null=False, blank=False)
    password=models.CharField(max_length=100)
    user_type=models.CharField(max_length=50)
    user_contact=models.CharField(max_length=100)
    # path = models.ImageField(upload_to='images/')
    path = models.ImageField(upload_to='images/',default='images/default.png')
    def __str__(self):  
        return self.username
    profile_picture = models.ImageField(upload_to='images/', blank=True, null=True)    
    user_isactive=models.DecimalField(max_digits=1,decimal_places=0, default=0)
    # add additional fields in here
  
    
class Pharmacy_Details(models.Model):
    pharmaname=models.CharField(max_length=300)
    pharmaweburl=models.CharField(max_length=150)
    proprietorname=models.CharField(max_length=100)
    proprietorcontact=models.CharField(max_length=12)
    proprietoremail=models.CharField(max_length=100)
    
    def __str__(self):
        return self.pharmaname

class ProductMaster(models.Model):
    productid=models.BigAutoField(primary_key=True, auto_created=True)
    product_name=models.CharField(max_length=200)
    product_company=models.CharField(max_length=200)
    product_packing=models.CharField(max_length=20)
    product_image=models.ImageField(upload_to='images/',default='images/medicine_default.png', null=True)
    product_salt=models.CharField(max_length=300, default=None)
    product_category=models.CharField(max_length=30, default=None)
    product_hsn=models.CharField(max_length=20, default=None)
    product_hsn_percent=models.CharField(max_length=20, default=None)
    product_barcode=models.CharField(max_length=50, blank=True, null=True, unique=True, help_text="Product barcode for scanning")
    
    def __str__(self):
        return f"{self.product_name} ({self.product_company})"
    
class SupplierMaster(models.Model):
    supplierid=models.BigAutoField(primary_key=True, auto_created=True)
    supplier_name=models.CharField(max_length=200)
    supplier_type=models.CharField(max_length=200, blank=True, default='')
    supplier_address=models.CharField(max_length=200, blank=True, default='')
    supplier_mobile=models.CharField(max_length=15)
    supplier_whatsapp=models.CharField(max_length=15, blank=True, default='')
    supplier_emailid=models.CharField(max_length=60, blank=True, default='')
    supplier_spoc=models.CharField(max_length=100, blank=True, default='')
    supplier_dlno=models.CharField(max_length=30, blank=True, default='')
    supplier_gstno=models.CharField(max_length=20, blank=True, default='')
    supplier_bank=models.CharField(max_length=200, blank=True, default='')
    supplier_branch=models.CharField(max_length=200, blank=True, default='NA')
    supplier_bankaccountno=models.CharField(max_length=30, blank=True, default='')
    supplier_bankifsc=models.CharField(max_length=20, blank=True, default='')
    supplier_upi=models.CharField(max_length=50, null=True, blank=True, default='')
    
    def __str__(self):
        return self.supplier_name

class CustomerMaster(models.Model):
    customerid=models.BigAutoField(primary_key=True, auto_created=True)
    customer_name=models.CharField(max_length=200, default='NA')
    customer_type=models.CharField(max_length=200, blank=True, default='TYPE-A')
    customer_address=models.CharField(max_length=200, blank=True, default='NA')
    customer_mobile=models.CharField(max_length=15, blank=True, default='NA')
    customer_whatsapp=models.CharField(max_length=15, blank=True, default='NA')
    customer_emailid=models.CharField(max_length=60, blank=True, default='NA')
    customer_spoc=models.CharField(max_length=100, blank=True, default='NA')
    customer_dlno=models.CharField(max_length=30, blank=True, default='NA')
    customer_gstno=models.CharField(max_length=20, blank=True, default='NA')
    customer_food_license_no=models.CharField(max_length=30, blank=True, default='NA')
    customer_credit_days=models.IntegerField(blank=True, default=0)
    
    def __str__(self):
        return self.customer_name

class InvoiceMaster(models.Model):
    invoiceid=models.BigAutoField(primary_key=True, auto_created=True)
    invoice_no=models.CharField(max_length=20)
    invoice_date=models.DateField(null=False, blank=False, default=timezone.now)
    supplierid=models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    transport_charges=models.FloatField()
    invoice_total=models.FloatField(null=False, blank=False)
    invoice_paid=models.FloatField(null=False, blank=False, default=0)
    payment_status=models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('overdue', 'Overdue')
    ], default='pending')
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['invoice_no', 'supplierid'], name='unique_invoiceno_supplierid')
        ]
    
    def __str__(self):
        return f"Invoice #{self.invoice_no} - {self.supplierid.supplier_name}"
    
    @property
    def balance_due(self):
        return self.invoice_total - self.invoice_paid

class InvoicePaid(models.Model):
    payment_id=models.BigAutoField(primary_key=True, auto_created=True)
    ip_invoiceid=models.ForeignKey(InvoiceMaster, on_delete=models.CASCADE)
    payment_date=models.DateField(null=False, blank=False, default=timezone.now)
    payment_amount=models.FloatField()
    payment_mode=models.CharField(max_length=30, null=True)
    payment_ref_no=models.CharField(max_length=30, null=True)
    
    def __str__(self):
        return f"Payment of {self.payment_amount} for Invoice #{self.ip_invoiceid.invoice_no}"

class PurchaseMaster(models.Model):
    purchaseid=models.BigAutoField(primary_key=True, auto_created=True) 
    product_supplierid=models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    product_invoiceid=models.ForeignKey(InvoiceMaster, on_delete=models.CASCADE, default=1)
    product_invoice_no=models.CharField(max_length=20)
    productid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name=models.CharField(max_length=200)
    product_company=models.CharField(max_length=200)
    product_packing=models.CharField(max_length=20)
    product_batch_no=models.CharField(max_length=20)
    product_expiry=models.CharField(max_length=7, help_text="Format: MM-YYYY") 
    product_MRP=models.FloatField()
    product_purchase_rate=models.FloatField()  
    product_quantity=models.FloatField()
    product_free_qty=models.FloatField(default=0.0)
    product_scheme=models.FloatField(default=0.0)
    product_discount_got=models.FloatField()
    product_transportation_charges=models.FloatField()   
    actual_rate_per_qty=models.FloatField(default=0.0)  
    product_actual_rate=models.FloatField(default=0.0)
    total_amount=models.FloatField(default=0.0)  
    purchase_entry_date=models.DateTimeField(default=timezone.now)
    CGST=models.FloatField(default=0.0)
    SGST=models.FloatField(default=0.0)
    purchase_calculation_mode=models.CharField(max_length=5, default='flat')
    rate_a=models.FloatField(default=0.0, blank=True)
    rate_b=models.FloatField(default=0.0, blank=True)
    rate_c=models.FloatField(default=0.0, blank=True)
    source_challan_no=models.CharField(max_length=50, blank=True, null=True)
    source_challan_date=models.DateField(blank=True, null=True)
    #calculation_mode indicates how discount is calculated by flat-rupees or %-percent
    
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.product_quantity}"

class SalesInvoiceMaster(models.Model):
    sales_invoice_no=models.CharField(primary_key=True, max_length=20)
    sales_invoice_date=models.DateField(null=False, blank=False)
    customerid=models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    invoice_series=models.ForeignKey('InvoiceSeries', on_delete=models.SET_NULL, null=True, blank=True)
    sales_transport_charges=models.FloatField(default=0)
    sales_invoice_paid=models.FloatField(null=False, blank=False, default=0)
    
    def __str__(self):
        return f"Sales Invoice #{self.sales_invoice_no} - {self.customerid.customer_name}"
    
    @property
    def sales_invoice_total(self):
        """Calculate total from the sum of all sales items"""
        from django.db.models import Sum
        sales_total = SalesMaster.objects.filter(sales_invoice_no=self.sales_invoice_no).aggregate(Sum('sale_total_amount'))
        return sales_total['sale_total_amount__sum'] or 0
    
    @property
    def balance_due(self):
        return self.sales_invoice_total - self.sales_invoice_paid

class SalesMaster(models.Model):
    id = models.BigAutoField(primary_key=True, auto_created=True)
    sales_invoice_no=models.ForeignKey(SalesInvoiceMaster, on_delete=models.CASCADE)
    customerid=models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    productid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name=models.CharField(max_length=200, default='NA')
    product_company=models.CharField(max_length=200, blank=True, default='NA')
    product_packing=models.CharField(max_length=20, blank=True, default='NA')
    product_batch_no=models.CharField(max_length=20)
    product_expiry=models.CharField(max_length=7, help_text="Format: MM-YYYY")
    product_MRP=models.FloatField(default=0.0)
    sale_rate=models.FloatField(default=0.0)
    sale_quantity=models.FloatField(default=0.0)
    sale_free_qty=models.FloatField(default=0.0)
    sale_scheme=models.FloatField(default=0.0)
    sale_discount=models.FloatField(default=0.0)
    sale_cgst=models.FloatField(default=0.0)
    sale_sgst=models.FloatField(default=0.0)
    sale_total_amount=models.FloatField(default=0.0)
    sale_entry_date=models.DateTimeField(default=timezone.now)
    rate_applied=models.CharField(max_length=10, blank=True, default='NA')
    sale_calculation_mode=models.CharField(max_length=5, default='flat') 
    #calculation_mode indicates how discount is calculated by flat-rupees or %-percent
    source_challan_no=models.CharField(max_length=50, blank=True, null=True, help_text='Source customer challan number if pulled from challan')
    source_challan_date=models.DateField(blank=True, null=True, help_text='Source customer challan date if pulled from challan')
   
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.sale_quantity}"

class SalesInvoicePaid(models.Model):
    sales_payment_id=models.BigAutoField(primary_key=True, auto_created=True)
    sales_ip_invoice_no=models.ForeignKey(SalesInvoiceMaster, on_delete=models.CASCADE)
    sales_payment_date=models.DateField(default=timezone.now)
    sales_payment_amount=models.FloatField()
    sales_payment_mode=models.CharField(max_length=30, default='NA')
    sales_payment_ref_no=models.CharField(max_length=30,default='NA')
    
    def __str__(self):
        return f"Payment of {self.sales_payment_amount} for Sales Invoice #{self.sales_ip_invoice_no.sales_invoice_no}"

class ProductRateMaster(models.Model):
    rate_productid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    rate_A=models.FloatField(default=0.0)
    rate_B=models.FloatField(default=0.0)
    rate_C=models.FloatField(default=0.0)
    rate_date=models.DateField(null=False, blank=False, default=timezone.now)
    
    def __str__(self):
        return f"Rates for {self.rate_productid.product_name} as of {self.rate_date}"

class ReturnInvoiceMaster(models.Model):
    returninvoiceid=models.CharField(primary_key=True, max_length=20)
    returninvoice_date=models.DateField(null=False, blank=False, default=timezone.now)
    returnsupplierid=models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    return_charges=models.FloatField(default=0)
    returninvoice_total=models.FloatField(null=False, blank=False)
    returninvoice_paid=models.FloatField(null=False, blank=False, default=0)
    
    def __str__(self):
        return f"Return Invoice #{self.returninvoiceid} - {self.returnsupplierid.supplier_name}"
    
    @property
    def balance_due(self):
        return self.returninvoice_total - self.returninvoice_paid

class PurchaseReturnInvoicePaid(models.Model):
    pr_payment_id=models.BigAutoField(primary_key=True, auto_created=True)
    pr_ip_returninvoiceid=models.ForeignKey(ReturnInvoiceMaster, on_delete=models.CASCADE)
    pr_payment_date=models.DateField(null=False, blank=False, default=timezone.now)
    pr_payment_amount=models.FloatField()
    pr_payment_mode=models.CharField(max_length=30, null=True)
    pr_payment_ref_no=models.CharField(max_length=30, null=True)
    
    def __str__(self):
        return f"Return Payment of {self.pr_payment_amount} for Return Invoice #{self.pr_ip_returninvoiceid.returninvoiceid}"

class ReturnPurchaseMaster(models.Model):
    returnpurchaseid=models.BigAutoField(primary_key=True, auto_created=True)
    returninvoiceid=models.ForeignKey(ReturnInvoiceMaster, on_delete=models.CASCADE, default=1) 
    returnproduct_supplierid=models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    returnproductid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    returnproduct_batch_no=models.CharField(max_length=20)
    returnproduct_expiry=models.DateField(help_text="Expiry date")
    returnproduct_MRP=models.FloatField(default=0.0)  
    returnproduct_purchase_rate=models.FloatField()  
    returnproduct_quantity=models.FloatField()
    returnproduct_free_qty=models.FloatField(default=0.0)
    returnproduct_cgst=models.FloatField(default=2.5)
    returnproduct_sgst=models.FloatField(default=2.5)
    returntotal_amount=models.FloatField(default=0.0)
    return_reason=models.CharField(max_length=200, blank=True, null=True)
    returnpurchase_entry_date=models.DateField(default=timezone.now)
    
    def __str__(self):
        return f"Return: {self.returnproductid.product_name} - {self.returnproduct_batch_no} - {self.returnproduct_quantity}"

class ReturnSalesInvoiceMaster(models.Model):
    return_sales_invoice_no=models.CharField(primary_key=True, max_length=20)
    return_sales_invoice_date=models.DateField(null=False, blank=False)
    return_sales_customerid=models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    return_sales_charges=models.FloatField(default=0)
    transport_charges=models.FloatField(default=0)
    sales_invoice_no = models.ForeignKey(SalesMaster, on_delete=models.CASCADE, related_name='returns',null=True)
    return_sales_invoice_total=models.FloatField(null=False, blank=False)
    return_sales_invoice_paid=models.FloatField(null=False, blank=False, default=0)
    created_at=models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Sales Return Invoice #{self.return_sales_invoice_no} - {self.return_sales_customerid.customer_name}"
    
    @property
    def balance_due(self):
        return self.return_sales_invoice_total - self.return_sales_invoice_paid

class ReturnSalesInvoicePaid(models.Model):
    return_sales_payment_id=models.BigAutoField(primary_key=True, auto_created=True)
    return_sales_ip_invoice_no=models.ForeignKey(ReturnSalesInvoiceMaster, on_delete=models.CASCADE)
    return_sales_payment_date=models.DateTimeField(default=timezone.now)
    return_sales_payment_amount=models.FloatField()
    return_sales_payment_mode=models.CharField(max_length=30, default='NA')
    return_sales_payment_ref_no=models.CharField(max_length=30,default='NA')
    
    def __str__(self):
        return f"Return Payment of {self.return_sales_payment_amount} for Return Sales Invoice #{self.return_sales_ip_invoice_no.return_sales_invoice_no}"

class ReturnSalesMaster(models.Model):
    RETURN_REASON_CHOICES = [
        ('', 'Select Reason'),
        ('non_moving', 'Non Moving'),
        ('breakage', 'Breakage'),
        ('expiry', 'Expiry'),
    ]
    
    return_sales_id=models.BigAutoField(primary_key=True, auto_created=True)
    return_sales_invoice_no=models.ForeignKey(ReturnSalesInvoiceMaster, on_delete=models.CASCADE)
    return_customerid=models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    return_productid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    return_product_name=models.CharField(max_length=200, default='NA')
    return_product_company=models.CharField(max_length=200, blank=True, default='NA')
    return_product_packing=models.CharField(max_length=20, blank=True, default='NA')
    return_product_batch_no=models.CharField(max_length=20)
    return_product_expiry=models.CharField(max_length=7, help_text="Format: MM-YYYY")
    return_product_MRP=models.FloatField(default=0.0)
    return_sale_rate=models.FloatField(default=0.0)
    return_sale_quantity=models.FloatField(default=0.0)
    return_sale_free_qty=models.FloatField(default=0.0)
    return_sale_scheme=models.FloatField(default=0.0)
    return_sale_discount=models.FloatField(default=0.0)
    return_sale_cgst=models.FloatField(default=0.0)
    return_sale_sgst=models.FloatField(default=0.0)
    return_sale_total_amount=models.FloatField(default=0.0)
    return_reason=models.CharField(max_length=200, blank=True, null=True, choices=RETURN_REASON_CHOICES)
    return_sale_entry_date=models.DateTimeField(default=timezone.now)
    return_sale_calculation_mode=models.CharField(max_length=20, default='percentage', choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')])
    
    def __str__(self):
        return f"Sales Return: {self.return_product_name} - {self.return_product_batch_no} - {self.return_sale_quantity}"

class SaleRateMaster(models.Model):
    productid=models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_batch_no=models.CharField(max_length=20)
    rate_A=models.FloatField(default=0.0)
    rate_B=models.FloatField(default=0.0)
    rate_C=models.FloatField(default=0.0)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['productid', 'product_batch_no'], name='unique_productid_product_batch_no')
        ]
        
    def __str__(self):
        return f"Batch Rates for {self.productid.product_name} - Batch {self.product_batch_no}"





class InvoiceSeries(models.Model):
    series_id = models.BigAutoField(primary_key=True, auto_created=True)
    series_name = models.CharField(max_length=10, unique=True)
    series_prefix = models.CharField(max_length=5, blank=True)
    current_number = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.series_name} (Current: {self.current_number})"
    
    def get_next_invoice_number(self):
        """Generate next invoice number for this series"""
        if self.series_prefix:
            invoice_no = f"{self.series_prefix}{self.current_number:07d}"
        else:
            invoice_no = f"{self.series_name}{self.current_number:07d}"
        
        # Increment counter
        self.current_number += 1
        self.save()
        
        return invoice_no
    
    class Meta:
        verbose_name_plural = "Invoice Series"

class Challan1(models.Model):
    challan_id = models.BigAutoField(primary_key=True, auto_created=True)
    challan_no = models.CharField(max_length=50, unique=True)
    challan_date = models.DateField(default=timezone.now)
    supplier = models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    challan_total = models.FloatField(default=0.0)
    transport_charges = models.FloatField(default=0.0)
    challan_paid = models.FloatField(default=0.0)
    challan_remark = models.TextField(default='None')
    is_invoiced = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Challan #{self.challan_no} - {self.supplier.supplier_name}"
    
    class Meta:
        db_table = 'challan1'
        ordering = ['-challan_date', '-challan_id']

class SupplierChallanMaster(models.Model):
    challan_id = models.BigAutoField(primary_key=True, auto_created=True)
    product_suppliername = models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    product_challan_id = models.ForeignKey(Challan1, on_delete=models.CASCADE)
    product_challan_no = models.CharField(max_length=50)
    product_id = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    product_company = models.CharField(max_length=200)
    product_packing = models.CharField(max_length=20)
    product_batch_no = models.CharField(max_length=20)
    product_expiry = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    product_mrp = models.FloatField()
    product_purchase_rate = models.FloatField()
    product_quantity = models.FloatField()
    product_free_qty = models.FloatField(default=0.0)
    product_scheme = models.FloatField(default=0.0)
    product_discount = models.FloatField(default=0.0)
    product_transportation_charges = models.FloatField(default=0.0)
    actual_rate_per_qty = models.FloatField(default=0.0)
    product_actual_rate = models.FloatField(default=0.0)
    total_amount = models.FloatField(default=0.0)
    challan_entry_date = models.DateTimeField(default=timezone.now)
    cgst = models.FloatField(default=2.5)
    sgst = models.FloatField(default=2.5)
    challan_calculation_mode = models.CharField(max_length=10, default='flat')
    rate_a=models.FloatField(default=0.0, blank=True)
    rate_b=models.FloatField(default=0.0, blank=True)
    rate_c=models.FloatField(default=0.0, blank=True)
    
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.product_quantity}"
    
    class Meta:
        db_table = 'supplier_challan_master'
        ordering = ['-challan_entry_date']

class SupplierChallanMaster2(models.Model):
    challan_id = models.BigAutoField(primary_key=True, auto_created=True)
    product_suppliername = models.ForeignKey(SupplierMaster, on_delete=models.CASCADE)
    product_challan_id = models.ForeignKey(Challan1, on_delete=models.CASCADE)
    product_challan_no = models.CharField(max_length=50)
    product_id = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    product_company = models.CharField(max_length=200)
    product_packing = models.CharField(max_length=20)
    product_batch_no = models.CharField(max_length=20)
    product_expiry = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    product_mrp = models.FloatField()
    product_purchase_rate = models.FloatField()
    product_quantity = models.FloatField()
    product_free_qty = models.FloatField(default=0.0)
    product_scheme = models.FloatField(default=0.0)
    product_discount = models.FloatField(default=0.0)
    product_transportation_charges = models.FloatField(default=0.0)
    actual_rate_per_qty = models.FloatField(default=0.0)
    product_actual_rate = models.FloatField(default=0.0)
    total_amount = models.FloatField(default=0.0)
    challan_entry_date = models.DateTimeField(default=timezone.now)
    cgst = models.FloatField(default=2.5)
    sgst = models.FloatField(default=2.5)
    challan_calculation_mode = models.CharField(max_length=10, default='flat')
    rate_a=models.FloatField(default=0.0, blank=True)
    rate_b=models.FloatField(default=0.0, blank=True)
    rate_c=models.FloatField(default=0.0, blank=True)
    
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.product_quantity}"
    
    class Meta:
        db_table = 'supplier_challan_master2'
        ordering = ['-challan_entry_date']

class ChallanSeries(models.Model):
    series_id = models.BigAutoField(primary_key=True, auto_created=True)
    series_name = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=True)
    created_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return self.series_name
    
    class Meta:
        verbose_name_plural = "Challan Series"

class CustomerChallan(models.Model):
    customer_challan_id = models.BigAutoField(primary_key=True, auto_created=True)
    customer_challan_no = models.CharField(max_length=50, unique=True)
    customer_challan_date = models.DateField(default=timezone.now)
    customer_name = models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    challan_series = models.ForeignKey('ChallanSeries', on_delete=models.SET_NULL, null=True, blank=True)
    customer_transport_charges = models.FloatField(default=0.0)
    challan_total = models.FloatField(default=0.0)
    challan_invoice_paid = models.FloatField(default=0.0)
    is_invoiced = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Customer Challan #{self.customer_challan_no} - {self.customer_name.customer_name}"
    
    class Meta:
        db_table = 'customer_challan'
        ordering = ['-customer_challan_date', '-customer_challan_id']

class CustomerChallanMaster(models.Model):
    customer_challan_master_id = models.BigAutoField(primary_key=True, auto_created=True)
    customer_challan_id = models.ForeignKey(CustomerChallan, on_delete=models.CASCADE)
    customer_challan_no = models.CharField(max_length=50)
    customer_name = models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    product_id = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    product_company = models.CharField(max_length=200)
    product_packing = models.CharField(max_length=20)
    product_batch_no = models.CharField(max_length=20)
    product_expiry = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    product_mrp = models.FloatField()
    sale_rate = models.FloatField()
    sale_quantity = models.FloatField()
    sale_free_qty = models.FloatField(default=0.0)
    sale_discount = models.FloatField(default=0.0)
    sale_cgst = models.FloatField(default=2.5)
    sale_sgst = models.FloatField(default=2.5)
    sale_total_amount = models.FloatField()
    sales_entry_date = models.DateTimeField(default=timezone.now)
    rate_applied = models.CharField(max_length=10, blank=True, default='NA')
    
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.sale_quantity}"
    
    class Meta:
        db_table = 'customer_challan_master'
        ordering = ['-sales_entry_date']

class CustomerChallanMaster2(models.Model):
    customer_challan_master_id = models.BigAutoField(primary_key=True, auto_created=True)
    customer_challan_id = models.ForeignKey(CustomerChallan, on_delete=models.CASCADE)
    customer_challan_no = models.CharField(max_length=50)
    customer_name = models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
    product_id = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    product_name = models.CharField(max_length=200)
    product_company = models.CharField(max_length=200)
    product_packing = models.CharField(max_length=20)
    product_batch_no = models.CharField(max_length=20)
    product_expiry = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    product_mrp = models.FloatField()
    sale_rate = models.FloatField()
    sale_quantity = models.FloatField()
    sale_discount = models.FloatField(default=0.0)
    sale_cgst = models.FloatField(default=2.5)
    sale_sgst = models.FloatField(default=2.5)
    sale_total_amount = models.FloatField()
    sales_entry_date = models.DateTimeField(default=timezone.now)
    rate_applied = models.CharField(max_length=10, blank=True, default='NA')
    
    def __str__(self):
        return f"{self.product_name} - {self.product_batch_no} - {self.sale_quantity}"
    
    class Meta:
        db_table = 'customer_challan_master2'
        ordering = ['-sales_entry_date']



# REMOVED: Sales Challan Invoice functionality
# class SalesChallanInvoice(models.Model):
#     sales_challan_invoice_id = models.BigAutoField(primary_key=True, auto_created=True)
#     invoice_no = models.CharField(max_length=50, unique=True)
#     invoice_date = models.DateField(default=timezone.now)
#     customer = models.ForeignKey(CustomerMaster, on_delete=models.CASCADE)
#     invoice_series = models.ForeignKey(InvoiceSeries, on_delete=models.SET_NULL, null=True, blank=True)
#     selected_challans = models.JSONField(default=list)  # Store challan IDs
#     invoice_total = models.FloatField(default=0.0)
#     invoice_paid = models.FloatField(default=0.0)
#     created_at = models.DateTimeField(default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)
#     
#     def __str__(self):
#         return f"Sales Challan Invoice #{self.invoice_no} - {self.customer.customer_name}"
#     
#     @property
#     def balance_due(self):
#         return self.invoice_total - self.invoice_paid
#     
#     class Meta:
#         db_table = 'sales_challan_invoice'
#         ordering = ['-invoice_date', '-sales_challan_invoice_id']

# class SalesChallanInvoicePaid(models.Model):
#     payment_id = models.BigAutoField(primary_key=True, auto_created=True)
#     sales_challan_invoice = models.ForeignKey(SalesChallanInvoice, on_delete=models.CASCADE)
#     payment_date = models.DateField(default=timezone.now)
#     payment_amount = models.FloatField()
#     payment_method = models.CharField(max_length=30, default='Cash')
#     payment_reference = models.CharField(max_length=30, default='NA')
#     
#     def __str__(self):
#         return f"Payment of ₹{self.payment_amount} for Sales Challan Invoice #{self.sales_challan_invoice.invoice_no}"
#     
#     class Meta:
#         db_table = 'sales_challan_invoice_paid'
#         ordering = ['-payment_date']

class StockIssueMaster(models.Model):
    """Model for managing stock issues/adjustments"""
    ISSUE_TYPES = [
        ('damage', 'Damage'),
        ('expiry', 'Expiry'),
        ('theft', 'Theft'),
        ('loss', 'Loss'),
        ('adjustment', 'Stock Adjustment'),
        ('transfer', 'Transfer Out'),
        ('sample', 'Sample Given'),
        ('other', 'Other'),
    ]
    
    issue_id = models.BigAutoField(primary_key=True, auto_created=True)
    issue_no = models.CharField(max_length=20, unique=True)
    issue_date = models.DateField(default=timezone.now)
    issue_type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    total_value = models.FloatField(default=0.0)
    remarks = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Web_User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'stock_issue_master'
        ordering = ['-issue_date', '-issue_id']
    
    def __str__(self):
        return f"Stock Issue #{self.issue_no} - {self.get_issue_type_display()}"
    
    def save(self, *args, **kwargs):
        if not self.issue_no:
            # Generate issue number
            last_issue = StockIssueMaster.objects.order_by('-issue_id').first()
            if last_issue:
                last_num = int(last_issue.issue_no.split('SI')[-1])
                self.issue_no = f"SI{last_num + 1:06d}"
            else:
                self.issue_no = "SI000001"
        super().save(*args, **kwargs)

class StockIssueDetail(models.Model):
    """Detail model for stock issue items"""
    detail_id = models.BigAutoField(primary_key=True, auto_created=True)
    issue = models.ForeignKey(StockIssueMaster, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE)
    batch_no = models.CharField(max_length=20)
    expiry_date = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    quantity_issued = models.FloatField(validators=[MinValueValidator(0.01)])
    unit_rate = models.FloatField(default=0.0)
    total_amount = models.FloatField(default=0.0)
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'stock_issue_detail'
        ordering = ['detail_id']
    
    def __str__(self):
        return f"{self.product.product_name} - Batch: {self.batch_no} - Qty: {self.quantity_issued}"
    
    def save(self, *args, **kwargs):
        self.total_amount = self.quantity_issued * self.unit_rate
        super().save(*args, **kwargs)



# ============================================
# CONTRA ENTRY MODULE - START
# ============================================
class ContraEntry(models.Model):
    """Model for Contra Entry - Fund transfer between Cash and Bank"""
    CONTRA_TYPES = [
        ('BANK_TO_CASH', 'Bank to Cash'),
        ('CASH_TO_BANK', 'Cash to Bank'),
    ]
    
    contra_id = models.BigAutoField(primary_key=True, auto_created=True)
    contra_no = models.CharField(max_length=20, unique=True)
    contra_date = models.DateField(default=timezone.now)
    contra_type = models.CharField(max_length=20, choices=CONTRA_TYPES)
    amount = models.FloatField(validators=[MinValueValidator(0.01)])
    from_account = models.CharField(max_length=100, help_text="Bank name or 'Cash'")
    to_account = models.CharField(max_length=100, help_text="Bank name or 'Cash'")
    reference_no = models.CharField(max_length=50, blank=True, null=True)
    narration = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(Web_User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contra_entry'
        ordering = ['-contra_date', '-contra_id']
        verbose_name = 'Contra Entry'
        verbose_name_plural = 'Contra Entries'
    
    def __str__(self):
        return f"Contra #{self.contra_no} - {self.get_contra_type_display()} - ₹{self.amount}"
    
    def save(self, *args, **kwargs):
        if not self.contra_no:
            # Generate contra number
            last_contra = ContraEntry.objects.order_by('-contra_id').first()
            if last_contra:
                last_num = int(last_contra.contra_no.split('CE')[-1])
                self.contra_no = f"CE{last_num + 1:06d}"
            else:
                self.contra_no = "CE000001"
        super().save(*args, **kwargs)
# ============================================
# CONTRA ENTRY MODULE - END
# ============================================

# ============================================
# INVENTORY CACHE TABLES - START
# ============================================
class ProductInventoryCache(models.Model):
    """Cache table for product-level inventory summary"""
    product = models.OneToOneField(ProductMaster, on_delete=models.CASCADE, primary_key=True, related_name='inventory_cache')
    
    # Stock Summary
    total_stock = models.FloatField(default=0, db_index=True, help_text="Total stock across all batches")
    total_batches = models.IntegerField(default=0, help_text="Number of active batches")
    
    # Financial Summary
    avg_mrp = models.FloatField(default=0, help_text="Average MRP across batches")
    avg_purchase_rate = models.FloatField(default=0, help_text="Average purchase rate")
    total_stock_value = models.FloatField(default=0, help_text="Total stock value (stock × MRP)")
    
    # Status
    stock_status = models.CharField(max_length=50, db_index=True, default='out_of_stock', 
                                    help_text="in_stock, low_stock, out_of_stock")
    has_expired_batches = models.BooleanField(default=False, db_index=True)
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    
    class Meta:
        db_table = 'product_inventory_cache'
        indexes = [
            models.Index(fields=['stock_status', 'total_stock']),
            models.Index(fields=['has_expired_batches']),
        ]
    
    def __str__(self):
        return f"Cache: {self.product.product_name} - Stock: {self.total_stock}"

class BatchInventoryCache(models.Model):
    """Cache table for batch-level inventory details"""
    product = models.ForeignKey(ProductMaster, on_delete=models.CASCADE, related_name='batch_caches')
    batch_no = models.CharField(max_length=20, db_index=True)
    expiry_date = models.CharField(max_length=7, help_text="Format: MM-YYYY")
    
    # Stock Details
    current_stock = models.FloatField(default=0, db_index=True)
    mrp = models.FloatField(default=0)
    purchase_rate = models.FloatField(default=0)
    
    # Rates
    rate_a = models.FloatField(default=0)
    rate_b = models.FloatField(default=0)
    rate_c = models.FloatField(default=0)
    
    # Status
    is_expired = models.BooleanField(default=False, db_index=True)
    expiry_status = models.CharField(max_length=20, default='valid', 
                                     help_text="expired, expiring_soon, valid")
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'batch_inventory_cache'
        unique_together = [['product', 'batch_no', 'expiry_date']]
        indexes = [
            models.Index(fields=['product', 'current_stock']),
            models.Index(fields=['is_expired']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_no']),
        ]
        ordering = ['expiry_date', 'batch_no']
    
    def __str__(self):
        return f"{self.product.product_name} - Batch: {self.batch_no} - Stock: {self.current_stock}"
# ============================================
# INVENTORY CACHE TABLES - END
# ============================================
