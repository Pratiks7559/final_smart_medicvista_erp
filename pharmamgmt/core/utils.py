from django.db.models import Sum, F
from django.utils import timezone
from io import BytesIO
from datetime import datetime, date
import tempfile
import os

from .models import PurchaseMaster, SalesMaster, ReturnPurchaseMaster, ReturnSalesMaster, ProductMaster


def parse_expiry_date(expiry_str):
    """
    Convert expiry string to datetime object
    Handles DDMMYYYY, MM-YYYY, and other formats
    """
    if not expiry_str or expiry_str == 'NA':
        return None
    
    from .date_utils import parse_ddmmyyyy_date, convert_legacy_dates
    from django.core.exceptions import ValidationError
    
    try:
        # First normalize the format
        normalized = normalize_expiry_date(expiry_str)
        
        # Parse using date_utils
        return parse_ddmmyyyy_date(normalized)
        
    except (ValueError, ValidationError):
        # Fallback for MM-YYYY format
        try:
            if '-' in str(expiry_str):
                month, year = map(int, str(expiry_str).split('-'))
                # Return last day of the month
                if month == 12:
                    return date(year + 1, 1, 1) - timezone.timedelta(days=1)
                else:
                    return date(year, month + 1, 1) - timezone.timedelta(days=1)
        except (ValueError, AttributeError):
            pass
        
        return None


def format_expiry_date(date_obj):
    """
    Convert datetime object to MM-YYYY string format
    """
    if not date_obj:
        return ""
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime("%m-%Y")


def validate_expiry_format(expiry_str):
    """
    Validate MM-YYYY format
    """
    if not expiry_str:
        return False
    try:
        parts = expiry_str.split('-')
        if len(parts) != 2:
            return False
        month, year = map(int, parts)
        return 1 <= int(month) <= 12 and 2000 <= int(year) <= 2050
    except (ValueError, AttributeError):
        return False


def get_batch_stock_status(product_id, batch_no, expiry_date=None, exclude_sale_id=None):
    """
    Calculate current stock and free qty for a specific product batch + expiry combination
    Returns a tuple of (available_quantity, available_free_qty, is_available)
    Enhanced with better error handling and user feedback
    Now includes stock issues in calculation - FIXED FOR UI UPDATE
    
    Args:
        product_id: Product ID
        batch_no: Batch number
        expiry_date: Expiry date (optional)
        exclude_sale_id: Sale ID to exclude from calculation (for edit mode)
    """
    try:
        from django.db.models import Sum
        
        # ⬆️ INCREASE: Purchase + Supplier Challan + Sales Return
        # Get total stock for batch from invoices
        batch_purchased_invoice = PurchaseMaster.objects.filter(
            productid=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('product_quantity'))['total'] or 0
        
        batch_purchased_free_invoice = PurchaseMaster.objects.filter(
            productid=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('product_free_qty'))['total'] or 0
        
        # Get total stock for batch from challans
        from .models import SupplierChallanMaster
        batch_purchased_challan = SupplierChallanMaster.objects.filter(
            product_id=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('product_quantity'))['total'] or 0
        
        batch_purchased_free_challan = SupplierChallanMaster.objects.filter(
            product_id=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('product_free_qty'))['total'] or 0
        
        batch_purchased = batch_purchased_invoice + batch_purchased_challan
        batch_purchased_free = batch_purchased_free_invoice + batch_purchased_free_challan
        
        # ⬇️ DECREASE: Sales + Customer Challan + Purchase Return
        # Get sold quantity from sales invoices, excluding specific sale if provided (for edit mode)
        sales_query = SalesMaster.objects.filter(
            productid=product_id, 
            product_batch_no=batch_no
        )
        
        if exclude_sale_id:
            sales_query = sales_query.exclude(id=exclude_sale_id)
        
        batch_sold_invoices = sales_query.aggregate(total=Sum('sale_quantity'))['total'] or 0
        batch_sold_free_invoices = sales_query.aggregate(total=Sum('sale_free_qty'))['total'] or 0
        
        # Get sold quantity from customer challans
        from .models import CustomerChallanMaster
        batch_sold_challans = CustomerChallanMaster.objects.filter(
            product_id=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        batch_sold_free_challans = CustomerChallanMaster.objects.filter(
            product_id=product_id, 
            product_batch_no=batch_no
        ).aggregate(total=Sum('sale_free_qty'))['total'] or 0
        
        batch_sold = batch_sold_invoices + batch_sold_challans
        batch_sold_free = batch_sold_free_invoices + batch_sold_free_challans
        
        # Purchase returns (reduces stock)
        purchase_returns = ReturnPurchaseMaster.objects.filter(
            returnproductid=product_id,
            returnproduct_batch_no=batch_no
        ).aggregate(total=Sum('returnproduct_quantity'))['total'] or 0
        
        purchase_returns_free = ReturnPurchaseMaster.objects.filter(
            returnproductid=product_id,
            returnproduct_batch_no=batch_no
        ).aggregate(total=Sum('returnproduct_free_qty'))['total'] or 0
        
        # Sales returns (increases stock)
        sales_returns = ReturnSalesMaster.objects.filter(
            return_productid=product_id,
            return_product_batch_no=batch_no
        ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
        
        sales_returns_free = ReturnSalesMaster.objects.filter(
            return_productid=product_id,
            return_product_batch_no=batch_no
        ).aggregate(total=Sum('return_sale_free_qty'))['total'] or 0
        
        # Get stock issues (reduces stock) - CRITICAL FOR UI UPDATE
        from .models import StockIssueDetail
        stock_issues = StockIssueDetail.objects.filter(
            product=product_id,
            batch_no=batch_no
        ).aggregate(total=Sum('quantity_issued'))['total'] or 0
        
        # ✅ FINAL CALCULATION (same formula for both stock and free qty)
        current_stock = batch_purchased - batch_sold - purchase_returns + sales_returns - stock_issues
        current_free_qty = batch_purchased_free - batch_sold_free - purchase_returns_free + sales_returns_free
        
        # Debug logging for stock issue tracking - Enhanced for troubleshooting
        print(f"[OK] Stock calculation for Product {product_id}, Batch {batch_no}:")
        print(f"   [+] Purchased: {batch_purchased} (Invoice: {batch_purchased_invoice} + Challan: {batch_purchased_challan})")
        print(f"   [+] Purchased Free: {batch_purchased_free} (Invoice: {batch_purchased_free_invoice} + Challan: {batch_purchased_free_challan})")
        print(f"   [-] Sold: {batch_sold} (Invoice: {batch_sold_invoices} + Challan: {batch_sold_challans})")
        print(f"   [-] Sold Free: {batch_sold_free} (Invoice: {batch_sold_free_invoices} + Challan: {batch_sold_free_challans})")
        print(f"   [R] Returns: Purchase(-{purchase_returns}) + Sales(+{sales_returns}) = {sales_returns - purchase_returns}")
        print(f"   [R] Returns Free: Purchase(-{purchase_returns_free}) + Sales(+{sales_returns_free}) = {sales_returns_free - purchase_returns_free}")
        print(f"   [!] Stock Issues: -{stock_issues}")
        print(f"   [=] Final Stock: {current_stock}, Free Qty: {current_free_qty} (Available: {current_stock > 0})")
        
        return current_stock, current_free_qty, float(current_stock) > 0
    except Exception as e:
        print(f"[ERROR] Error processing inventory for Product {product_id}, Batch {batch_no}: {e}")
        return 0, 0, False


def get_stock_status(product_id):
    """
    Calculate current stock for a product using StockManager
    Includes sales from both SalesMaster and CustomerChallanMaster
    Now includes stock issues in calculation
    """
    try:
        from .stock_manager import StockManager
        from .models import CustomerChallanMaster, StockIssueDetail
        from django.db.models import Sum
        
        stock_summary = StockManager.get_stock_summary(product_id)
        
        # Get total sold from sales invoices
        total_sold_invoices = SalesMaster.objects.filter(
            productid=product_id
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        # Get total sold from customer challans
        total_sold_challans = CustomerChallanMaster.objects.filter(
            product_id=product_id
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        total_sold_combined = total_sold_invoices + total_sold_challans
        
        # Get total stock issues (reduces stock)
        total_stock_issues = StockIssueDetail.objects.filter(
            product=product_id
        ).aggregate(total=Sum('quantity_issued'))['total'] or 0
        
        # Recalculate current stock including stock issues
        current_stock_with_issues = stock_summary['total_stock'] - total_stock_issues
        
        # Convert to legacy format for backward compatibility
        expiry_stock = []
        total_free_qty = 0
        for batch in stock_summary['batches']:
            # Get additional batch details
            purchase = PurchaseMaster.objects.filter(
                productid=product_id,
                product_batch_no=batch['batch_no']
            ).first()
            
            if purchase:
                # Get stock issues for this batch
                batch_stock_issues = StockIssueDetail.objects.filter(
                    product=product_id,
                    batch_no=batch['batch_no']
                ).aggregate(total=Sum('quantity_issued'))['total'] or 0
                
                # Calculate batch stock including issues
                batch_stock_with_issues = batch['stock'] - batch_stock_issues

                # Calculate free qty for this batch
                batch_free_purchased = PurchaseMaster.objects.filter(
                    productid=product_id,
                    product_batch_no=batch['batch_no']
                ).aggregate(total=Sum('product_free_qty'))['total'] or 0

                batch_free_sold = SalesMaster.objects.filter(
                    productid=product_id,
                    product_batch_no=batch['batch_no']
                ).aggregate(total=Sum('sale_free_qty'))['total'] or 0

                batch_free_qty = max(0, batch_free_purchased - batch_free_sold)
                total_free_qty += batch_free_qty
                
                expiry_stock.append({
                    'batch_no': batch['batch_no'],
                    'expiry': batch['expiry'],
                    'quantity': batch_stock_with_issues,
                    'free_qty': batch_free_qty,
                    'total_qty': batch_stock_with_issues + batch_free_qty,
                    'purchase_rate': purchase.product_purchase_rate,
                    'mrp': purchase.product_MRP
                })
        
        return {
            'purchased': stock_summary['total_purchased'],
            'sold': total_sold_combined,
            'purchase_returns': stock_summary['total_purchase_returns'],
            'sales_returns': stock_summary['total_sales_returns'],
            'stock_issues': total_stock_issues,
            'current_stock': current_stock_with_issues,
            'total_free_qty': total_free_qty,
            'current_stock_with_free': current_stock_with_issues + total_free_qty,
            'expiry_stock': expiry_stock
        }
    except Exception as e:
        print(f"Error in get_stock_status: {e}")
        return {
            'purchased': 0,
            'sold': 0,
            'purchase_returns': 0,
            'sales_returns': 0,
            'stock_issues': 0,
            'current_stock': 0,
            'total_free_qty': 0,
            'current_stock_with_free': 0,
            'expiry_stock': []
        }


def generate_invoice_pdf(invoice):
    """
    Generate a PDF for purchase invoice
    Note: This is a placeholder function. In a real implementation, 
    you would use a PDF library like ReportLab or WeasyPrint
    """
    # In a real implementation, you would create a PDF here
    # For now, this is just a placeholder
    return None


def generate_sales_invoice_pdf(invoice):
    """
    Generate a PDF for sales invoice
    Note: This is a placeholder function. In a real implementation, 
    you would use a PDF library like ReportLab or WeasyPrint
    """
    # In a real implementation, you would create a PDF here
    # For now, this is just a placeholder
    return None


def get_fy_label(fy_year):
    """Return FY label string e.g. 2026-27 for fy_year=2026"""
    return f"{fy_year}-{str(fy_year + 1)[2:]}"


def get_fy_date_range(fy_year):
    """Return (start_date, end_date) for a financial year starting April 1."""
    from datetime import date
    return date(fy_year, 4, 1), date(fy_year + 1, 3, 31)


def generate_sales_invoice_number(series_id=None, fy_year=None):
    """
    Generate next FY-wise sales invoice number.
    Format: <PREFIX><6-digit>  e.g. GVP000001

    Logic:
      - Filter SalesInvoiceMaster by series + FY date range
      - Find MAX numeric suffix from existing invoice numbers
      - Increment by 1, pad to 6 digits
      - Reset to 000001 for each new FY
    """
    from .models import InvoiceSeries, SalesInvoiceMaster
    from .year_filter_utils import get_current_financial_year
    from django.db import transaction

    if fy_year is None:
        fy_year = get_current_financial_year()

    fy_start, fy_end = get_fy_date_range(fy_year)

    def _next_number_for_series(series):
        prefix = series.series_prefix or series.series_name
        with transaction.atomic():
            # Get all invoices for this series in this FY
            fy_invoices = SalesInvoiceMaster.objects.select_for_update().filter(
                invoice_series=series,
                sales_invoice_date__gte=fy_start,
                sales_invoice_date__lte=fy_end,
            ).values_list('sales_invoice_no', flat=True)

            # Extract numeric suffix and find max
            max_num = 0
            for inv_no in fy_invoices:
                try:
                    suffix = inv_no.replace(prefix, '', 1)
                    num = int(suffix)
                    if num > max_num:
                        max_num = num
                except (ValueError, TypeError):
                    continue

            next_num = max_num + 1
            invoice_no = f"{prefix}{next_num:06d}"

            # Ensure uniqueness (edge case guard)
            while SalesInvoiceMaster.objects.filter(sales_invoice_no=invoice_no).exists():
                next_num += 1
                invoice_no = f"{prefix}{next_num:06d}"

        return invoice_no

    if series_id:
        try:
            series = InvoiceSeries.objects.get(series_id=series_id, is_active=True)
            return _next_number_for_series(series)
        except InvoiceSeries.DoesNotExist:
            pass

    # Fallback: ABC series
    abc_series, _ = InvoiceSeries.objects.get_or_create(
        series_name='ABC',
        defaults={'series_prefix': 'ABC', 'current_number': 1, 'is_active': True}
    )
    return _next_number_for_series(abc_series)


def get_avg_mrp(product_id):
    """
    Calculate the average MRP for a product - Optimized version
    """
    from django.db.models import Avg
    
    # Get average MRP directly from database
    avg_data = PurchaseMaster.objects.filter(
        productid_id=product_id
    ).aggregate(
        avg_mrp=Avg('product_MRP')
    )
    
    return avg_data['avg_mrp'] or 0.0


def get_product_batches_info(product_id):
    """
    Get all batch information for a product with stock details including returns
    Fixed to track stock separately by batch + expiry date combination
    """
    from django.db.models import Sum
    
    batches = []
    
    # Get all unique batch + expiry combinations from purchases
    purchase_combinations = PurchaseMaster.objects.filter(
        productid=product_id
    ).values('product_batch_no', 'product_expiry').distinct()
    
    # Also get combinations from sales, returns to ensure completeness
    sales_combinations = SalesMaster.objects.filter(
        productid=product_id
    ).values('product_batch_no', 'product_expiry').distinct()
    
    pr_combinations = ReturnPurchaseMaster.objects.filter(
        returnproductid=product_id
    ).values('returnproduct_batch_no', 'returnproduct_expiry').distinct()
    
    sr_combinations = ReturnSalesMaster.objects.filter(
        return_productid=product_id
    ).values('return_product_batch_no', 'return_product_expiry').distinct()
    
    # Combine all unique batch + expiry combinations
    all_combinations = set()
    
    for combo in purchase_combinations:
        all_combinations.add((combo['product_batch_no'], combo['product_expiry']))
    
    for combo in sales_combinations:
        all_combinations.add((combo['product_batch_no'], combo['product_expiry']))
    
    for combo in pr_combinations:
        all_combinations.add((combo['returnproduct_batch_no'], combo['returnproduct_expiry']))
    
    for combo in sr_combinations:
        all_combinations.add((combo['return_product_batch_no'], combo['return_product_expiry']))
    
    for batch_no, expiry_date in all_combinations:
        # Calculate stock for this specific batch + expiry combination
        batch_purchased = PurchaseMaster.objects.filter(
            productid=product_id, 
            product_batch_no=batch_no,
            product_expiry=expiry_date
        ).aggregate(total=Sum('product_quantity'))['total'] or 0
        
        batch_sold = SalesMaster.objects.filter(
            productid=product_id, 
            product_batch_no=batch_no,
            product_expiry=expiry_date
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        # Include returns in calculation for this specific batch + expiry
        purchase_returns = ReturnPurchaseMaster.objects.filter(
            returnproductid=product_id,
            returnproduct_batch_no=batch_no,
            returnproduct_expiry=expiry_date
        ).aggregate(total=Sum('returnproduct_quantity'))['total'] or 0
        
        sales_returns = ReturnSalesMaster.objects.filter(
            return_productid=product_id,
            return_product_batch_no=batch_no,
            return_product_expiry=expiry_date
        ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
        
        # Correct stock calculation: Purchased - Sold - Purchase Returns + Sales Returns
        batch_stock = batch_purchased - batch_sold - purchase_returns + sales_returns
        
        # Include all batches with any activity (for complete inventory tracking)
        if batch_stock != 0 or batch_purchased > 0:
            # Normalize expiry date format
            normalized_expiry = normalize_expiry_date(expiry_date)
            batches.append({
                'batch_no': batch_no,
                'expiry': normalized_expiry,
                'stock': batch_stock
            })
    
    # Sort by expiry date (earliest first)
    batches.sort(key=lambda x: x['expiry'] if x['expiry'] else '9999-12-31')
    
    return batches

def get_bulk_inventory_data(product_ids=None, search_query=None, limit=None):
    """
    Optimized function to get inventory data for multiple products at once
    Reduces database queries significantly
    """
    from django.db.models import Subquery, OuterRef, Value, Q, Avg
    from django.db.models.functions import Coalesce
    
    # Base queryset with select_related for better performance
    products_query = ProductMaster.objects.all().order_by('product_name')
    
    # Apply filters
    if product_ids:
        products_query = products_query.filter(productid__in=product_ids)
    
    if search_query:
        products_query = products_query.filter(
            Q(product_name__icontains=search_query) | 
            Q(product_company__icontains=search_query) |
            Q(product_category__icontains=search_query)
        )
    
    if limit:
        products_query = products_query[:limit]
    
    # Annotate with stock calculations using optimized subqueries including returns
    products_with_stock = products_query.annotate(
        total_purchased=Coalesce(
            Subquery(
                PurchaseMaster.objects.filter(
                    productid=OuterRef('productid')
                ).aggregate(total=Sum('product_quantity'))['total']
            ), Value(0)
        ),
        total_sold=Coalesce(
            Subquery(
                SalesMaster.objects.filter(
                    productid=OuterRef('productid')
                ).aggregate(total=Sum('sale_quantity'))['total']
            ), Value(0)
        ),
        total_purchase_returns=Coalesce(
            Subquery(
                ReturnPurchaseMaster.objects.filter(
                    returnproductid=OuterRef('productid')
                ).aggregate(total=Sum('returnproduct_quantity'))['total']
            ), Value(0)
        ),
        total_sales_returns=Coalesce(
            Subquery(
                ReturnSalesMaster.objects.filter(
                    return_productid=OuterRef('productid')
                ).aggregate(total=Sum('return_sale_quantity'))['total']
            ), Value(0)
        ),
        avg_mrp=Coalesce(
            Subquery(
                PurchaseMaster.objects.filter(
                    productid=OuterRef('productid')
                ).aggregate(avg_mrp=Avg('product_MRP'))['avg_mrp']
            ), Value(0.0)
        )
    ).annotate(
        # Correct stock calculation: Purchased - Sold - Purchase Returns + Sales Returns
        current_stock=F('total_purchased') - F('total_sold') - F('total_purchase_returns') + F('total_sales_returns')
    ).annotate(
        stock_value=F('current_stock') * F('avg_mrp')
    )
    
    return products_with_stock

def normalize_expiry_date(expiry_input):
    """
    Normalize expiry date to consistent format
    Handles MM-YYYY format and converts to YYYY-MM-DD for Django compatibility
    """
    if not expiry_input:
        return ""
    
    try:
        # Convert to string if it's a date object
        if hasattr(expiry_input, 'strftime'):
            return expiry_input.strftime("%Y-%m-%d")
        
        expiry_str = str(expiry_input).strip()
        
        # Handle MM-YYYY format (convert to YYYY-MM-DD)
        if '-' in expiry_str and len(expiry_str.split('-')) == 2:
            parts = expiry_str.split('-')
            if len(parts[0]) <= 2 and len(parts[1]) == 4:  # MM-YYYY
                month, year = int(parts[0]), int(parts[1])
                # Convert to last day of month in YYYY-MM-DD format
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                return f"{year}-{month:02d}-{last_day:02d}"
        
        # Handle YYYY-MM-DD format (already correct)
        if len(expiry_str) == 10 and expiry_str.count('-') == 2:
            parts = expiry_str.split('-')
            if len(parts[0]) == 4:  # YYYY-MM-DD
                return expiry_str
        
        # Use date utilities for other formats
        from .date_utils import convert_legacy_dates, parse_ddmmyyyy_date
        from django.core.exceptions import ValidationError
        
        try:
            normalized = convert_legacy_dates(expiry_str)
            date_obj = parse_ddmmyyyy_date(normalized)
            return date_obj.strftime("%Y-%m-%d")
        except (ValidationError, Exception):
            pass
        
    except Exception as e:
        print(f"Error normalizing expiry date '{expiry_input}': {e}")
    
    # Return as-is if format is not recognized
    return str(expiry_input).strip()


def get_inventory_batches_info(product_id):
    """
    Get all batch information for inventory display with stock details
    Simplified to avoid MM-YYYY date format issues
    FIXED: Now properly includes stock issues in calculation for UI updates
    """
    from django.db.models import Sum
    from .models import SaleRateMaster, StockIssueDetail
    
    batches = []
    
    try:
        # Get unique batches from both purchases and challans
        from .models import SupplierChallanMaster
        
        invoice_batches = PurchaseMaster.objects.filter(productid=product_id).values('product_batch_no').distinct()
        challan_batches = SupplierChallanMaster.objects.filter(product_id=product_id).values('product_batch_no').distinct()
        
        # Combine unique batch numbers
        all_batch_nos = set()
        for b in invoice_batches:
            all_batch_nos.add(b['product_batch_no'])
        for b in challan_batches:
            all_batch_nos.add(b['product_batch_no'])
        
        print(f"[INFO] Processing inventory for Product {product_id} - Found {len(all_batch_nos)} unique batches")
        
        for batch_no in all_batch_nos:
            # Calculate stock from invoices
            batch_purchased_invoice = PurchaseMaster.objects.filter(
                productid=product_id, 
                product_batch_no=batch_no
            ).aggregate(total=Sum('product_quantity'))['total'] or 0
            
            # Calculate stock from challans
            batch_purchased_challan = SupplierChallanMaster.objects.filter(
                product_id=product_id, 
                product_batch_no=batch_no
            ).aggregate(total=Sum('product_quantity'))['total'] or 0
            
            batch_purchased = batch_purchased_invoice + batch_purchased_challan
            
            # Calculate sold from sales invoices
            batch_sold_invoices = SalesMaster.objects.filter(
                productid=product_id, 
                product_batch_no=batch_no
            ).aggregate(total=Sum('sale_quantity'))['total'] or 0
            
            # Calculate sold from customer challans
            from .models import CustomerChallanMaster
            batch_sold_challans = CustomerChallanMaster.objects.filter(
                product_id=product_id, 
                product_batch_no=batch_no
            ).aggregate(total=Sum('sale_quantity'))['total'] or 0
            
            batch_sold = batch_sold_invoices + batch_sold_challans
            
            # Include returns in calculation
            purchase_returns = ReturnPurchaseMaster.objects.filter(
                returnproductid=product_id,
                returnproduct_batch_no=batch_no
            ).aggregate(total=Sum('returnproduct_quantity'))['total'] or 0
            
            sales_returns = ReturnSalesMaster.objects.filter(
                return_productid=product_id,
                return_product_batch_no=batch_no
            ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
            
            # CRITICAL FIX: Include stock issues in calculation (reduces stock)
            batch_stock_issues = StockIssueDetail.objects.filter(
                product=product_id,
                batch_no=batch_no
            ).aggregate(total=Sum('quantity_issued'))['total'] or 0
            
            # Calculate stock (includes customer challan sales and stock issues) - FIXED CALCULATION
            batch_stock = batch_purchased - batch_sold - purchase_returns + sales_returns - batch_stock_issues
            
            # Enhanced logging for UI debugging
            if batch_stock_issues > 0:
                print(f"   [!] Batch {batch_no}: Stock Issues = {batch_stock_issues}, Final Stock = {batch_stock}")
            
            # Get MRP from first purchase or challan record
            first_purchase = PurchaseMaster.objects.filter(
                productid=product_id,
                product_batch_no=batch_no
            ).first()
            
            if not first_purchase:
                first_challan = SupplierChallanMaster.objects.filter(
                    product_id=product_id,
                    product_batch_no=batch_no
                ).first()
                if first_challan:
                    # Create a pseudo purchase object for compatibility
                    class PseudoPurchase:
                        def __init__(self, challan):
                            self.product_expiry = challan.product_expiry
                            self.product_MRP = challan.product_mrp
                    first_purchase = PseudoPurchase(first_challan)
            
            # Get batch rates
            batch_rates = {'rate_A': 0, 'rate_B': 0, 'rate_C': 0}
            try:
                sale_rate = SaleRateMaster.objects.get(
                    productid=product_id, product_batch_no=batch_no
                )
                batch_rates = {
                    'rate_A': float(sale_rate.rate_A or 0),
                    'rate_B': float(sale_rate.rate_B or 0),
                    'rate_C': float(sale_rate.rate_C or 0)
                }
            except SaleRateMaster.DoesNotExist:
                pass
            
            # Include all batches - FIXED: Now shows correct stock after issues
            batches.append({
                'batch_no': batch_no,
                'expiry': first_purchase.product_expiry if first_purchase else '',
                'stock': batch_stock,  # This now includes stock issues deduction
                'mrp': first_purchase.product_MRP if first_purchase else 0,
                'rates': batch_rates
            })
    
    except Exception as e:
        print(f"[ERROR] Error processing inventory for Product {product_id}: {str(e)}")
    
    return batches

