from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import ProductMaster
from .forms import ProductForm
import json

@login_required
@require_http_methods(["POST"])
def add_product_api(request):
    """
    API endpoint to add product via AJAX from any form
    Returns JSON response with product details
    """
    try:
        # Get form data
        form = ProductForm(request.POST, request.FILES)
        
        if form.is_valid():
            product = form.save()
            
            return JsonResponse({
                'success': True,
                'message': f"Product '{product.product_name}' added successfully!",
                'product': {
                    'id': product.productid,
                    'name': product.product_name,
                    'company': product.product_company,
                    'packing': product.product_packing,
                    'salt': product.product_salt,
                    'category': product.product_category,
                    'hsn': product.product_hsn,
                    'hsn_percent': product.product_hsn_percent,
                    'barcode': product.product_barcode or ''
                }
            })
        else:
            # Return validation errors
            errors = {}
            for field, error_list in form.errors.items():
                errors[field] = [str(error) for error in error_list]
            
            return JsonResponse({
                'success': False,
                'error': 'Validation failed',
                'errors': errors
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
