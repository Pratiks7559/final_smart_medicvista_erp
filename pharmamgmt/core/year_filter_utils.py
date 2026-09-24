from datetime import datetime, date

def get_current_financial_year():
    """Get current financial year (April to March)"""
    today = date.today()
    if today.month >= 4:  # April se December
        return today.year
    else:  # January se March
        return today.year - 1

def get_financial_year_dates(fy_year):
    """Get start and end date for financial year"""
    start_date = date(fy_year, 4, 1)  # 1 April
    end_date = date(fy_year + 1, 3, 31)  # 31 March next year
    return start_date, end_date

def is_date_in_financial_year(value, fy_year):
    """Return whether a date belongs to the selected financial year."""
    if not value:
        return False
    if isinstance(value, datetime):
        value = value.date()
    start_date, end_date = get_financial_year_dates(fy_year)
    return start_date <= value <= end_date

def apply_year_filter(queryset, request, date_field):
    """
    Apply financial year filter (1 April to 31 March)
    
    Args:
        queryset: Django queryset to filter
        request: HTTP request object
        date_field: Name of the date field to filter on
    
    Returns:
        Filtered queryset
    """
    selected_year = request.session.get('selected_year', get_current_financial_year())
    start_date, end_date = get_financial_year_dates(selected_year)
    
    filter_kwargs = {
        f'{date_field}__gte': start_date,
        f'{date_field}__lte': end_date
    }
    
    return queryset.filter(**filter_kwargs)
