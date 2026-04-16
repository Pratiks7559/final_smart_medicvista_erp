from django import template
from decimal import Decimal
from datetime import datetime, date
import locale

register = template.Library()

# Try to set locale for Indian Rupee formatting
try:
    locale.setlocale(locale.LC_ALL, 'en_IN.UTF-8')
except:
    # Fallback to default locale if Indian locale not available
    locale.setlocale(locale.LC_ALL, '')

@register.filter(name='add_class')
def add_class(value, arg):
    """
    Safely add a CSS class to a Django form field widget.
    If value is not a form field (e.g. a string), return it unchanged.
    """
    try:
        return value.as_widget(attrs={'class': arg})
    except AttributeError:
        return value


@register.filter
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return value - arg
        except Exception:
            return 0

@register.filter
def currency(value):
    """Formats a value as a currency (₹) with 2 decimal places."""
    try:
        # Format with 2 decimal places
        float_value = float(value)
        return f"₹ {float_value:,.2f}"
    except (ValueError, TypeError):
        return f"₹ 0.00"

@register.filter
def subtract(value, arg):
    """Alias for sub filter."""
    return sub(value, arg)

@register.filter
def add(value, arg):
    """Adds the arg to the value."""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except Exception:
            return 0

@register.filter
def absolute(value):
    """Returns the absolute value."""
    try:
        return abs(float(value))
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divides the value by the arg."""
    try:
        arg = float(arg)
        if arg == 0:
            return 0
        return float(value) / arg
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiplies the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def mul(value, arg):
    """Alias for multiply filter."""
    return multiply(value, arg)

@register.filter
def percentage(value, arg=100):
    """Calculates value as a percentage of arg."""
    try:
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def sum_field(value, field_name):
    """
    Returns the sum of a specified field for a list of dictionaries or objects.
    
    Usage:
    {{ queryset|sum_field:'field_name' }}
    """
    try:
        total = 0
        for item in value:
            # Handle both dictionary-like and object-like access
            try:
                # Dictionary-like access
                val = item[field_name]
            except (KeyError, TypeError):
                try:
                    # Object-like access
                    val = getattr(item, field_name)
                except (AttributeError, TypeError):
                    val = 0
                    
            # Try to convert to numeric value
            try:
                if isinstance(val, (int, float, Decimal)):
                    total += float(val)
                else:
                    total += float(val or 0)
            except (ValueError, TypeError):
                # Skip if we can't convert to a number
                pass
                
        return total
    except Exception:
        return 0

@register.filter
def inr_format(value):
    """
    Format a number as Indian Rupees (INR) with rounded values.
    
    Examples:
        1234.56 -> ₹ 1,235
        1234567.89 -> ₹ 12,34,568
    """
    try:
        # Convert to float first and round to nearest integer
        value = round(float(value))
        
        # Format with commas using Indian numbering system
        if value < 0:
            sign = "-"
            value = abs(value)
        else:
            sign = ""
            
        # First format with conventional commas
        formatted = f"{value:,}"
        
        # Handle special case for Indian format
        integer_part = formatted
        
        # Don't format small numbers
        if len(integer_part.replace(',', '')) <= 3:
            return f"₹ {sign}{formatted}"
        
        # Custom format for Indian system (lakh, crore)
        # First remove existing commas
        integer_part = integer_part.replace(',', '')
        
        # Format in Indian style (3,2,2,...)
        result = integer_part[-3:]  # Last 3 digits
        integer_part = integer_part[:-3]  # Remaining digits
        
        # Add commas every 2 digits
        while integer_part:
            result = integer_part[-2:] + ',' + result if integer_part[-2:] else integer_part + ',' + result
            integer_part = integer_part[:-2]
        
        return f"₹ {sign}{result}"
    except (ValueError, TypeError):
        return "₹ 0"

@register.filter
def round_value(value):
    """
    Formats a floating point value with 2 decimal places.
    """
    try:
        return f"{float(value):.2f}"
    except (ValueError, TypeError):
        return "0.00"

@register.filter
def date_ddmmyyyy(value):
    """Format date as DDMMYYYY"""
    if not value:
        return ""
    
    try:
        if isinstance(value, str):
            if len(value) == 8 and value.isdigit():
                return value  # Already in DDMMYYYY format
            elif len(value) == 10 and '-' in value:
                # Convert YYYY-MM-DD to DDMMYYYY
                date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                return date_obj.strftime('%d%m%Y')
        elif isinstance(value, (date, datetime)):
            return value.strftime('%d%m%Y')
    except (ValueError, TypeError):
        pass
    
    return str(value)

@register.filter
def date_display(value):
    """Format date as DD/MM/YYYY for display - handles timezone-aware datetime"""
    if not value:
        return ""
    
    try:
        # Handle timezone-aware datetime objects
        if hasattr(value, 'date'):
            # If it's a datetime object, get the date part
            return value.date().strftime('%d/%m/%Y')
        elif isinstance(value, date):
            # If it's already a date object
            return value.strftime('%d/%m/%Y')
        elif isinstance(value, str):
            if len(value) == 8 and value.isdigit():
                # Convert DDMMYYYY to DD/MM/YYYY
                return f"{value[:2]}/{value[2:4]}/{value[4:8]}"
            elif len(value) == 10 and '-' in value:
                # Convert YYYY-MM-DD to DD/MM/YYYY
                date_obj = datetime.strptime(value, '%Y-%m-%d').date()
                return date_obj.strftime('%d/%m/%Y')
        
        # Fallback: try to convert to string and parse
        str_value = str(value)
        if len(str_value) >= 10:
            # Try to extract date from string representation
            date_part = str_value[:10]  # Get YYYY-MM-DD part
            if '-' in date_part:
                date_obj = datetime.strptime(date_part, '%Y-%m-%d').date()
                return date_obj.strftime('%d/%m/%Y')
                
    except (ValueError, TypeError, AttributeError):
        pass
    
    return str(value) if value else ""

@register.filter
def date_backend(value):
    """Format date as YYYY-MM-DD for backend"""
    if not value:
        return ""
    
    try:
        if isinstance(value, str):
            if len(value) == 8 and value.isdigit():
                # Convert DDMMYYYY to YYYY-MM-DD
                day = value[:2]
                month = value[2:4]
                year = value[4:8]
                return f"{year}-{month}-{day}"
            elif len(value) == 10 and '-' in value:
                return value  # Already in backend format
        elif isinstance(value, (date, datetime)):
            return value.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        pass
    
    return str(value)

@register.filter
def safe_date(value, format_string="d-m-Y"):
    """Safely format date, return empty string if None or invalid"""
    if not value:
        return ""
    
    try:
        if isinstance(value, (date, datetime)):
            return value.strftime(format_string.replace('d', '%d').replace('m', '%m').replace('Y', '%Y'))
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return ""

@register.filter
def normalize_expiry(value):
    """Normalize expiry date to consistent DD-MM-YYYY format"""
    if not value:
        return ""
    
    # Convert to string if it's a date object
    if hasattr(value, 'strftime'):
        return value.strftime("%d-%m-%Y")
    
    expiry_str = str(value).strip()
    
    # Handle DDMMYYYY format - convert to DD-MM-YYYY
    if len(expiry_str) == 8 and expiry_str.isdigit():
        day = expiry_str[:2]
        month = expiry_str[2:4]
        year = expiry_str[4:8]
        return f"{day}-{month}-{year}"
    
    # Handle YYYY-MM-DD format
    if len(expiry_str) == 10 and expiry_str.count('-') == 2:
        try:
            parts = expiry_str.split('-')
            if len(parts[0]) == 4:  # YYYY-MM-DD
                year = int(parts[0])
                month = int(parts[1])
                day = int(parts[2])
                return f"{day:02d}-{month:02d}-{year}"
        except:
            pass
    
    # Handle MM-YYYY format (convert to last day of month)
    if '-' in expiry_str:
        parts = expiry_str.split('-')
        if len(parts) == 2:
            try:
                month = int(parts[0])
                year = int(parts[1])
                if len(parts[1]) == 2:  # Convert YY to YYYY
                    year = 2000 + year
                
                # Get last day of month
                if month in [1,3,5,7,8,10,12]:
                    last_day = 31
                elif month in [4,6,9,11]:
                    last_day = 30
                else:  # February
                    last_day = 29 if year % 4 == 0 else 28
                
                return f"{last_day:02d}-{month:02d}-{year}"
            except ValueError:
                pass
    
    # Handle MMYY format (4 digits)
    if len(expiry_str) == 4 and expiry_str.isdigit():
        month = int(expiry_str[:2])
        year = 2000 + int(expiry_str[2:4])
        
        # Get last day of month
        if month in [1,3,5,7,8,10,12]:
            last_day = 31
        elif month in [4,6,9,11]:
            last_day = 30
        else:  # February
            last_day = 29 if year % 4 == 0 else 28
        
        return f"{last_day:02d}-{month:02d}-{year}"
    
    # Return as-is if format is not recognized
    return expiry_str

@register.filter
def datetime_display(value):
    """Format datetime for display with proper time"""
    if not value:
        return ""
    
    try:
        if isinstance(value, str):
            # Try to parse string datetime
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except:
                return value
        elif hasattr(value, 'strftime'):
            dt = value
        else:
            return str(value)
        
        # Format as "DD MMM YYYY, HH:MM"
        return dt.strftime("%d %b %Y, %H:%M")
    except (ValueError, TypeError, AttributeError):
        return str(value)

@register.filter
def time_ago(value):
    """Show how long ago a datetime was"""
    if not value:
        return ""
    
    try:
        from django.utils import timezone
        
        if isinstance(value, str):
            # Try to parse string datetime
            try:
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
            except:
                return ""
        elif hasattr(value, 'strftime'):
            dt = value
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt)
        else:
            return ""
        
        now = timezone.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    except Exception:
        return ""

@register.filter
def expiry_mmyyyy(value):
    """Convert expiry date to MM-YYYY format"""
    if not value:
        return ""
    
    expiry_str = str(value).strip()
    
    # If already in MM-YYYY format, return as-is
    if len(expiry_str) == 7 and expiry_str.count('-') == 1:
        parts = expiry_str.split('-')
        if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 4:
            return expiry_str
    
    # Handle YYYY-MM-DD format - convert to MM-YYYY
    if len(expiry_str) == 10 and expiry_str.count('-') == 2:
        try:
            parts = expiry_str.split('-')
            if len(parts[0]) == 4:  # YYYY-MM-DD
                year = parts[0]
                month = parts[1]
                return f"{month}-{year}"
        except:
            pass
    
    # Handle DDMMYYYY format - convert to MM-YYYY
    if len(expiry_str) == 8 and expiry_str.isdigit():
        month = expiry_str[2:4]
        year = expiry_str[4:8]
        return f"{month}-{year}"
    
    # Handle MMYY format - convert to MM-YYYY
    if len(expiry_str) == 4 and expiry_str.isdigit():
        month = expiry_str[:2]
        year = "20" + expiry_str[2:4]
        return f"{month}-{year}"
    
    # Handle DD-MM-YYYY format - convert to MM-YYYY
    if len(expiry_str) == 10 and expiry_str.count('-') == 2:
        try:
            parts = expiry_str.split('-')
            if len(parts[2]) == 4:  # DD-MM-YYYY
                month = parts[1]
                year = parts[2]
                return f"{month}-{year}"
        except:
            pass
    
    # Return as-is if format is not recognized
    return expiry_str

@register.filter
def slice_list(value, chunk_size):
    """Slice a list into chunks of specified size with global counter"""
    try:
        chunk_size = int(chunk_size)
        result = []
        for i in range(0, len(value), chunk_size):
            chunk = list(value[i:i + chunk_size])
            # Add global counter to each item
            for j, item in enumerate(chunk):
                item.global_counter = i + j + 1
            result.append(chunk)
        return result
    except (ValueError, TypeError):
        return [value]

@register.filter
def calculate_cgst_total(purchases):
    """Calculate total CGST amount from purchases"""
    try:
        total = 0
        for purchase in purchases:
            # Calculate CGST amount: (base_amount * cgst_rate) / 100
            base_amount = purchase.product_purchase_rate * purchase.product_quantity
            if purchase.purchase_calculation_mode == 'flat':
                base_amount -= purchase.product_discount_got
            else:
                base_amount *= (1 - (purchase.product_discount_got / 100))
            
            cgst_amount = (base_amount * purchase.CGST) / 100
            total += cgst_amount
        return total
    except Exception:
        return 0

@register.filter
def calculate_sgst_total(purchases):
    """Calculate total SGST amount from purchases"""
    try:
        total = 0
        for purchase in purchases:
            # Calculate SGST amount: (base_amount * sgst_rate) / 100
            base_amount = purchase.product_purchase_rate * purchase.product_quantity
            if purchase.purchase_calculation_mode == 'flat':
                base_amount -= purchase.product_discount_got
            else:
                base_amount *= (1 - (purchase.product_discount_got / 100))
            
            sgst_amount = (base_amount * purchase.SGST) / 100
            total += sgst_amount
        return total
    except Exception:
        return 0

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key"""
    try:
        return dictionary.get(key, [])
    except (AttributeError, TypeError):
        return []

@register.filter
def subtotal_amount(purchases):
    """Calculate subtotal (rate * qty) before discount for a list of purchases"""
    try:
        return sum(float(p.product_purchase_rate) * float(p.product_quantity) for p in purchases)
    except Exception:
        return 0

@register.filter
def total_discount(purchases):
    """Calculate total discount amount for a list of purchases"""
    try:
        total = 0
        for p in purchases:
            base = float(p.product_purchase_rate) * float(p.product_quantity)
            disc = float(p.product_discount_got)
            total += (base * disc / 100) if p.purchase_calculation_mode == 'perc' else disc
        return total
    except Exception:
        return 0

@register.filter
def taxable_amount(purchases):
    """Calculate taxable amount (subtotal - discount) for a list of purchases"""
    try:
        return float(subtotal_amount(purchases)) - float(total_discount(purchases))
    except Exception:
        return 0

@register.filter
def total_gst(purchases):
    """Calculate total GST (CGST + SGST) for a list of purchases"""
    try:
        total = 0
        for p in purchases:
            base = float(p.product_purchase_rate) * float(p.product_quantity)
            disc = float(p.product_discount_got)
            disc_amt = (base * disc / 100) if p.purchase_calculation_mode == 'perc' else disc
            taxable = base - disc_amt
            total += taxable * (float(p.CGST) + float(p.SGST)) / 100
        return total
    except Exception:
        return 0