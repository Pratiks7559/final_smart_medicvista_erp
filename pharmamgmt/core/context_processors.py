from core.year_filter_utils import get_current_financial_year

def year_context(request):
    """Add financial year context to all templates"""
    current_fy = get_current_financial_year()
    year_range = range(2011, max(current_fy, 2025) + 2)
    selected_year = request.session.get('selected_year', current_fy)
    
    return {
        'year_range': reversed(year_range),
        'selected_year': selected_year,
        'current_financial_year': current_fy
    }
