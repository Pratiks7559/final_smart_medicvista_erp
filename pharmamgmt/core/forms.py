from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    Web_User, Pharmacy_Details, ProductMaster, SupplierMaster, CustomerMaster,
    InvoiceMaster, InvoicePaid, PurchaseMaster, SalesInvoiceMaster, SalesMaster,
    SalesInvoicePaid, ProductRateMaster, ReturnInvoiceMaster, PurchaseReturnInvoicePaid,
    ReturnPurchaseMaster, ReturnSalesInvoiceMaster, ReturnSalesInvoicePaid, ReturnSalesMaster,
    SaleRateMaster
)

class DateInput(forms.TextInput):
    input_type = 'text'
    
    def __init__(self, attrs=None, format=None):
        default_attrs = {
            'class': 'form-control date-input-ddmmyyyy',
            'placeholder': 'DDMMYYYY',
            'maxlength': '8',
            'title': 'Enter date in DDMMYYYY format',
            'data-date-format': 'ddmmyyyy'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))

class UserRegistrationForm(UserCreationForm):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    ]
    
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    user_contact = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    path = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Web_User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2', 'user_type', 'user_contact', 'path']

class UserUpdateForm(forms.ModelForm):
    USER_TYPE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('staff', 'Staff'),
        ('customer', 'Customer'),
    ]
    
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    user_contact = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    path = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Web_User
        fields = ['first_name', 'last_name', 'email', 'user_type', 'user_contact', 'path']

class PharmacyDetailsForm(forms.ModelForm):
    pharmaname = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    pharmaweburl = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    proprietorname = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    proprietorcontact = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    proprietoremail = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = Pharmacy_Details
        fields = '__all__'

class ProductForm(forms.ModelForm):
    CATEGORY_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('powder', 'Powder'),
        ('drops', 'Drops'),
        ('other', 'Other'),
    ]
    
    product_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_company = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_packing = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_salt = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_category = forms.ChoiceField(choices=CATEGORY_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    product_hsn = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_hsn_percent = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_barcode = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scan or enter product barcode'}))
    product_image = forms.ImageField(required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    
    def clean_product_barcode(self):
        barcode = self.cleaned_data.get('product_barcode')
        # Convert empty string to None
        if not barcode or barcode.strip() == '':
            return None
        # Only check for duplicates if barcode is provided and not empty
        existing = ProductMaster.objects.filter(product_barcode=barcode)
        if self.instance.pk:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise forms.ValidationError("Product with this barcode already exists.")
        return barcode
    
    class Meta:
        model = ProductMaster
        fields = ['product_name', 'product_company', 'product_packing', 'product_salt', 
                  'product_category', 'product_hsn', 'product_hsn_percent', 'product_barcode', 'product_image']

class SupplierForm(forms.ModelForm):
    supplier_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_type = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_address = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    supplier_mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_whatsapp = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_emailid = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control'}))
    supplier_spoc = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_dlno = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_gstno = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_bank = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_branch = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_bankaccountno = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_bankifsc = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    supplier_upi = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = SupplierMaster
        fields = '__all__'

class CustomerForm(forms.ModelForm):
    CUSTOMER_TYPE_CHOICES = [
        ('TYPE-A', 'Type A'),
        ('TYPE-B', 'Type B'),
        ('TYPE-C', 'Type C'),
    ]
    
    customer_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    customer_mobile = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    customer_type = forms.ChoiceField(choices=CUSTOMER_TYPE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}), required=False)
    customer_address = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), required=False)
    customer_whatsapp = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    customer_emailid = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}), required=False)
    customer_spoc = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    customer_dlno = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    customer_gstno = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    customer_food_license_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}), required=False)
    customer_credit_days = forms.IntegerField(widget=forms.NumberInput(attrs={'class': 'form-control'}), required=False, initial=0)
    
    class Meta:
        model = CustomerMaster
        fields = ['customer_name', 'customer_type', 'customer_address', 'customer_mobile', 'customer_whatsapp', 'customer_emailid', 'customer_spoc', 'customer_dlno', 'customer_gstno', 'customer_food_license_no', 'customer_credit_days']

class InvoiceForm(forms.ModelForm):
    invoice_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    invoice_date = forms.CharField(widget=DateInput())
    supplierid = forms.ModelChoiceField(queryset=SupplierMaster.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    transport_charges = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), initial=0)
    invoice_total = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    
    def clean_invoice_date(self):
        from datetime import datetime
        date_str = self.cleaned_data['invoice_date']
        if not date_str:
            raise forms.ValidationError("Date is required.")
        date_str = str(date_str).strip()
        parsed = None

        if len(date_str) == 10 and '-' in date_str:
            try:
                parsed = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise forms.ValidationError("Invalid date format.")
        elif len(date_str) == 8 and date_str.isdigit():
            day = int(date_str[:2])
            month = int(date_str[2:4])
            year = int(date_str[4:8])
            try:
                parsed = datetime(year, month, day).date()
            except ValueError:
                raise forms.ValidationError("Invalid date")
        else:
            raise forms.ValidationError("Enter date in DDMMYYYY format")

        current_year = datetime.now().year
        if parsed.year < 1990:
            raise forms.ValidationError(
                f"Year {parsed.year} seems incorrect. "
                f"Please use DDMMYYYY format (e.g. {parsed.day:02d}{parsed.month:02d}{current_year})."
            )
        if parsed.year > current_year + 1:
            raise forms.ValidationError(f"Year {parsed.year} is too far in the future.")

        return parsed
    
    class Meta:
        model = InvoiceMaster
        fields = ['invoice_no', 'invoice_date', 'supplierid', 'transport_charges', 'invoice_total']

class InvoicePaymentForm(forms.ModelForm):
    payment_date = forms.DateField(widget=DateInput(attrs={'class': 'form-control'}))
    payment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    payment_mode = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    payment_ref_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    def clean_payment_date(self):
        from django.utils import timezone
        from datetime import datetime
        
        payment_date = self.cleaned_data.get('payment_date')
        
        if payment_date and hasattr(payment_date, 'date'):
            # Convert date to timezone-aware datetime
            current_time = timezone.now().time()
            payment_date = timezone.make_aware(
                datetime.combine(payment_date, current_time)
            )
        
        return payment_date
    
    class Meta:
        model = InvoicePaid
        fields = ['payment_date', 'payment_amount', 'payment_mode', 'payment_ref_no']
        exclude = ['ip_invoiceid']

class PurchaseForm(forms.ModelForm):
    product_batch_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_expiry = forms.CharField(
        max_length=7, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MM-YYYY',
            'title': 'Enter expiry date in MM-YYYY format (e.g., 12-2025)',
            'pattern': r'^(0[1-9]|1[0-2])-\d{4}$'
        })
    )
    product_MRP = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    product_purchase_rate = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    product_quantity = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    product_scheme = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    product_discount_got = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    CGST = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    SGST = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    CALC_MODE_CHOICES = [
        ('flat', 'Flat Amount'),
        ('perc', 'Percentage'),
    ]
    purchase_calculation_mode = forms.ChoiceField(choices=CALC_MODE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    
    # Fields for batch-specific sale rates
    rate_A = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), required=False)
    rate_B = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), required=False)
    rate_C = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), required=False)
    
    def clean_product_expiry(self):
        expiry = self.cleaned_data.get('product_expiry')
        if expiry:
            # Validate MM-YYYY format
            import re
            if not re.match(r'^(0[1-9]|1[0-2])-\d{4}$', expiry):
                raise forms.ValidationError('Enter expiry date in MM-YYYY format (e.g., 12-2025)')
            
            # Validate month and year values
            try:
                month, year = expiry.split('-')
                month = int(month)
                year = int(year)
                
                if month < 1 or month > 12:
                    raise forms.ValidationError('Invalid month. Use 01-12.')
                if year < 2020 or year > 2050:
                    raise forms.ValidationError('Invalid year. Use a year between 2020-2050.')
                    
            except ValueError:
                raise forms.ValidationError('Enter expiry date in MM-YYYY format (e.g., 12-2025)')
        
        return expiry
    
    class Meta:
        model = PurchaseMaster
        fields = ['productid', 'product_batch_no', 'product_expiry', 'product_MRP',
                 'product_purchase_rate', 'product_quantity', 'product_scheme',
                 'product_discount_got', 'CGST', 'SGST', 'purchase_calculation_mode',
                 'rate_A', 'rate_B', 'rate_C']
        exclude = ['product_supplierid', 'product_invoiceid', 'product_invoice_no',
                  'product_name', 'product_company', 'product_packing',
                  'product_transportation_charges', 'actual_rate_per_qty',
                  'product_actual_rate', 'total_amount', 'purchase_entry_date']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['productid'].queryset = ProductMaster.objects.all()
        self.fields['productid'].widget.attrs.update({'class': 'form-control'})
        self.fields['productid'].label = 'Product'

class SalesInvoiceForm(forms.ModelForm):
    sales_invoice_date = forms.CharField(widget=DateInput())
    customerid = forms.ModelChoiceField(queryset=CustomerMaster.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    sales_transport_charges = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), initial=0)
    
    def clean_sales_invoice_date(self):
        from datetime import datetime
        date_str = self.cleaned_data['sales_invoice_date']
        if not date_str:
            raise forms.ValidationError("Date is required.")
        date_str = str(date_str).strip()
        parsed = None

        # Handle YYYY-MM-DD format (from HTML date input)
        if len(date_str) == 10 and '-' in date_str:
            try:
                parsed = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                raise forms.ValidationError("Invalid date format.")

        # Handle DDMMYYYY format (manual entry)
        elif len(date_str) == 8 and date_str.isdigit():
            day = int(date_str[:2])
            month = int(date_str[2:4])
            year = int(date_str[4:8])
            try:
                parsed = datetime(year, month, day).date()
            except ValueError:
                raise forms.ValidationError("Invalid date. Please check day, month and year values.")

        else:
            raise forms.ValidationError("Enter date in DDMMYYYY format (e.g. 15012025)")

        # Year range validation - reject clearly wrong years only
        current_year = datetime.now().year
        if parsed.year < 1990:
            raise forms.ValidationError(
                f"Year {parsed.year} seems incorrect. "
                f"Please use DDMMYYYY format (e.g. {parsed.day:02d}{parsed.month:02d}{current_year})."
            )
        if parsed.year > current_year + 1:
            raise forms.ValidationError(
                f"Year {parsed.year} is too far in the future. Please enter a valid date."
            )

        return parsed
    
    class Meta:
        model = SalesInvoiceMaster
        fields = ['sales_invoice_date', 'customerid', 'sales_transport_charges']

class SalesForm(forms.ModelForm):
    product_batch_no = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control',
        'id': 'batch_no_field'
    }))
    product_expiry = forms.CharField(
        max_length=7, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly',
            'placeholder': 'MM-YYYY',
            'title': 'Expiry date in MM-YYYY format'
        })
    )
    sale_rate = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}))
    sale_quantity = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    sale_scheme = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    sale_discount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    sale_igst = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    custom_rate = forms.FloatField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    RATE_CHOICES = [
        ('A', 'Rate A'),
        ('B', 'Rate B'),
        ('C', 'Rate C'),
        ('custom', 'Custom Rate'),
    ]
    rate_applied = forms.ChoiceField(choices=RATE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    CALC_MODE_CHOICES = [
        ('flat', 'Flat Amount'),
        ('perc', 'Percentage'),
    ]
    sale_calculation_mode = forms.ChoiceField(choices=CALC_MODE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    
    class Meta:
        model = SalesMaster
        fields = ['productid', 'product_batch_no', 'product_expiry', 
                 'sale_rate', 'sale_quantity', 'sale_scheme',
                 'sale_discount', 'sale_igst', 'custom_rate', 'rate_applied', 'sale_calculation_mode']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['productid'].queryset = ProductMaster.objects.all()
        self.fields['productid'].widget.attrs.update({'class': 'form-control'})
        self.fields['productid'].label = 'Product'

class SalesPaymentForm(forms.ModelForm):
    sales_payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    sales_payment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('online', 'Online Transfer'),
        ('upi', 'UPI'),
    ]
    sales_payment_mode = forms.ChoiceField(choices=PAYMENT_MODE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    sales_payment_ref_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    

    
    class Meta:
        model = SalesInvoicePaid
        fields = ['sales_payment_date', 'sales_payment_amount', 'sales_payment_mode', 'sales_payment_ref_no']
        exclude = ['sales_ip_invoice_no']

class ProductRateForm(forms.ModelForm):
    rate_A = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    rate_B = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    rate_C = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    rate_date = forms.DateField(widget=DateInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = ProductRateMaster
        fields = ['rate_productid', 'rate_A', 'rate_B', 'rate_C', 'rate_date']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rate_productid'].queryset = ProductMaster.objects.all()
        self.fields['rate_productid'].widget.attrs.update({'class': 'form-control'})
        self.fields['rate_productid'].label = 'Product'

class PurchaseReturnInvoiceForm(forms.ModelForm):
    returninvoiceid = forms.CharField(required=False, widget=forms.HiddenInput())
    returninvoice_date = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control date-input-ddmmyyyy',
            'placeholder': 'DD-MM-YYYY',
            'maxlength': '10',
            'title': 'Enter return date in DD-MM-YYYY format'
        })
    )
    returnsupplierid = forms.ModelChoiceField(queryset=SupplierMaster.objects.all(), widget=forms.Select(attrs={'class': 'form-control'}))
    return_charges = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), initial=0.0, required=False)
    returninvoice_total = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), initial=0.0)
    
    def clean_returninvoice_date(self):
        from datetime import datetime
        from django.core.exceptions import ValidationError
        
        date_str = self.cleaned_data['returninvoice_date']
        
        # Handle YYYY-MM-DD format (from backend)
        if len(date_str) == 10 and '-' in date_str:
            try:
                # Check if it's DD-MM-YYYY format
                if date_str[2] == '-' and date_str[5] == '-':
                    day, month, year = date_str.split('-')
                    return datetime(int(year), int(month), int(day)).date()
                # Check if it's YYYY-MM-DD format
                elif date_str[4] == '-' and date_str[7] == '-':
                    return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        raise ValidationError("Enter date in DD-MM-YYYY format")
    
    class Meta:
        model = ReturnInvoiceMaster
        fields = ['returninvoiceid', 'returninvoice_date', 'returnsupplierid', 'return_charges', 'returninvoice_total']

class PurchaseReturnForm(forms.ModelForm):
    returnproduct_batch_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    returnproduct_expiry = forms.CharField(
        max_length=10, 
        widget=forms.TextInput(attrs={
            'class': 'form-control date-input', 
            'placeholder': 'DDMM',
            'maxlength': '4',
            'title': 'Enter expiry date in DDMM format. Year will be auto-completed.'
        })
    )
    
    def clean_returnproduct_expiry(self):
        from datetime import datetime
        date_str = self.cleaned_data.get('returnproduct_expiry', '')
        
        # Handle YYYY-MM-DD format from date picker
        if len(date_str) == 10 and '-' in date_str:
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        # Handle DDMM format
        if len(date_str) == 4 and date_str.isdigit():
            day = int(date_str[:2])
            month = int(date_str[2:4])
            year = datetime.now().year
            try:
                return datetime(year, month, day).date()
            except ValueError:
                raise forms.ValidationError("Invalid date")
        
        raise forms.ValidationError("Enter date in DDMM format")
    returnproduct_MRP = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    returnproduct_purchase_rate = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    returnproduct_quantity = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    returnproduct_scheme = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    returnproduct_charges = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    
    class Meta:
        model = ReturnPurchaseMaster
        fields = ['returnproductid', 'returnproduct_batch_no', 'returnproduct_expiry', 
                 'returnproduct_MRP', 'returnproduct_purchase_rate', 
                 'returnproduct_quantity', 'returnproduct_scheme', 'returnproduct_charges',
                 'return_reason']
        exclude = ['returninvoiceid', 'returnproduct_supplierid', 'returntotal_amount', 'returnpurchase_entry_date']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['returnproductid'].queryset = ProductMaster.objects.all()
        self.fields['returnproductid'].widget.attrs.update({'class': 'form-control'})
        self.fields['returnproductid'].label = 'Product'

class SalesReturnInvoiceForm(forms.ModelForm):
    return_sales_invoice_no = forms.CharField(required=False, widget=forms.HiddenInput())
    return_sales_invoice_date = forms.DateField(
        widget=DateInput(attrs={
            'class': 'form-control',
            'required': 'required',
            'placeholder': 'Select Date'
        }),
        required=True
    )
    return_sales_customerid = forms.ModelChoiceField(
        queryset=CustomerMaster.objects.all().order_by('customer_name'),
        widget=forms.Select(attrs={
            'class': 'form-control select2',
            'required': 'required',
            'placeholder': 'Select Customer'
        }),
        required=True,
        empty_label="Select Customer"
    )
    return_sales_charges = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'placeholder': 'Enter Charges'
        }),
        initial=0.0,
        required=False
    )
    return_sales_invoice_total = forms.FloatField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0',
            'required': 'required',
            'placeholder': 'Total Amount'
        }),
        initial=0.0,
        required=True
    )
    
    class Meta:
        model = ReturnSalesInvoiceMaster
        fields = ['return_sales_invoice_no', 'return_sales_invoice_date', 'return_sales_customerid', 
                 'return_sales_charges', 'return_sales_invoice_total']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add labels and help text
        self.fields['return_sales_invoice_date'].label = 'Return Date'
        self.fields['return_sales_customerid'].label = 'Customer'
        self.fields['return_sales_charges'].label = 'Additional Charges'
        self.fields['return_sales_invoice_total'].label = 'Total Amount'

class SalesReturnForm(forms.ModelForm):
    return_product_batch_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    return_product_expiry = forms.CharField(
        max_length=7, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MM-YYYY',
            'title': 'Enter expiry date in MM-YYYY format (e.g., 12-2025)',
            'pattern': r'^(0[1-9]|1[0-2])-\d{4}$'
        })
    )
    return_product_MRP = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_sale_rate = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_sale_quantity = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_sale_scheme = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}), required=False, initial=0)
    return_sale_discount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_sale_igst = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    return_reason = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    return_sale_calculation_mode = forms.ChoiceField(
        choices=[('percentage', 'Percentage'), ('fixed', 'Fixed Amount')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='percentage'
    )
    
    def clean_return_product_expiry(self):
        expiry = self.cleaned_data.get('return_product_expiry')
        if expiry:
            # Validate MM-YYYY format
            import re
            if not re.match(r'^(0[1-9]|1[0-2])-\d{4}$', expiry):
                raise forms.ValidationError('Enter expiry date in MM-YYYY format (e.g., 12-2025)')
            
            # Validate month and year values
            try:
                month, year = expiry.split('-')
                month = int(month)
                year = int(year)
                
                if month < 1 or month > 12:
                    raise forms.ValidationError('Invalid month. Use 01-12.')
                if year < 2020 or year > 2050:
                    raise forms.ValidationError('Invalid year. Use a year between 2020-2050.')
                    
            except ValueError:
                raise forms.ValidationError('Enter expiry date in MM-YYYY format (e.g., 12-2025)')
        
        return expiry
    
    class Meta:
        model = ReturnSalesMaster
        fields = ['return_productid', 'return_product_batch_no', 'return_product_expiry',
                 'return_product_MRP', 'return_sale_rate', 'return_sale_quantity', 'return_sale_scheme',
                 'return_sale_discount', 'return_sale_igst', 'return_reason',
                 'return_sale_calculation_mode']
        exclude = ['return_sales_invoice_no', 'return_customerid', 'return_product_name',
                  'return_product_company', 'return_product_packing',
                  'return_sale_total_amount', 'return_sale_entry_date']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['return_productid'].queryset = ProductMaster.objects.all()
        self.fields['return_productid'].widget.attrs.update({'class': 'form-control'})
        self.fields['return_productid'].label = 'Product'

SalesReturnItemFormSet = forms.formset_factory(SalesReturnForm, extra=1)

class SalesReturnPaymentForm(forms.ModelForm):
    return_sales_payment_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    return_sales_payment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('online', 'Online Transfer'),
        ('upi', 'UPI'),
    ]
    return_sales_payment_mode = forms.ChoiceField(choices=PAYMENT_MODE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    return_sales_payment_ref_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    

    
    class Meta:
        model = ReturnSalesInvoicePaid
        fields = ['return_sales_payment_date', 'return_sales_payment_amount', 'return_sales_payment_mode', 'return_sales_payment_ref_no']
        exclude = ['return_sales_ip_invoice_no']

        
class SaleRateForm(forms.ModelForm):
    productid = forms.ModelChoiceField(
        queryset=ProductMaster.objects.all().order_by('product_name'),
        widget=forms.Select(attrs={'class': 'form-control select2'})
    )
    product_batch_no = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    rate_A = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    rate_B = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    rate_C = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    
    class Meta:
        model = SaleRateMaster
        fields = ['productid', 'product_batch_no', 'rate_A', 'rate_B', 'rate_C']




class PaymentForm(forms.ModelForm):
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    payment_amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('bank_transfer', 'Bank Transfer'),
        ('upi', 'UPI'),
    ]
    payment_mode = forms.ChoiceField(choices=PAYMENT_MODE_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    payment_ref_no = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    ip_invoiceid = forms.ModelChoiceField(queryset=InvoiceMaster.objects.all(), widget=forms.HiddenInput())
    
    class Meta:
        model = InvoicePaid
        fields = ['payment_date', 'payment_amount', 'payment_mode', 'payment_ref_no', 'ip_invoiceid']

class ReceiptForm(forms.Form):
    receipt_date = forms.DateField(widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    receipt_amount = forms.FloatField(widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    receipt_method = forms.ChoiceField(
        choices=[
            ('cash', 'Cash'),
            ('cheque', 'Cheque'),
            ('bank_transfer', 'Bank Transfer'),
            ('upi', 'UPI'),
            ('card', 'Card')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    receipt_description = forms.CharField(required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    receipt_reference = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))