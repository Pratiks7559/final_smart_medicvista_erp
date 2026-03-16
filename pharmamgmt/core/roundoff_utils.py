"""
Utility functions for round-off calculations across all invoice types
"""

def calculate_roundoff(amount):
    """
    Calculate round-off amount and rounded total
    
    Args:
        amount (float): Original amount
        
    Returns:
        dict: {
            'original_amount': float,
            'rounded_amount': float,
            'roundoff_amount': float,
            'roundoff_type': str ('added' or 'deducted')
        }
    """
    original_amount = float(amount)
    rounded_amount = round(original_amount)
    roundoff_amount = rounded_amount - original_amount
    
    return {
        'original_amount': original_amount,
        'rounded_amount': rounded_amount,
        'roundoff_amount': abs(roundoff_amount),
        'roundoff_type': 'added' if roundoff_amount > 0 else 'deducted'
    }


def apply_roundoff(amount):
    """
    Simple function to round amount to nearest integer
    
    Args:
        amount (float): Amount to round
        
    Returns:
        float: Rounded amount
    """
    return round(float(amount))


def format_roundoff_display(original, rounded):
    """
    Format round-off for display
    
    Args:
        original (float): Original amount
        rounded (float): Rounded amount
        
    Returns:
        str: Formatted string like "+0.50" or "-0.25"
    """
    diff = rounded - original
    sign = '+' if diff >= 0 else ''
    return f"{sign}{diff:.2f}"
