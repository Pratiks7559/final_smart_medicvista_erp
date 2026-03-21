"""
Refresh Inventory Cache View
Allows users to manually rebuild inventory cache from UI
"""
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .inventory_cache import rebuild_all_cache
import threading


@login_required
def refresh_inventory_cache(request):
    """
    Manually trigger inventory cache rebuild
    Runs in background thread to avoid timeout
    """
    if request.method == 'POST':
        try:
            # Check if user has permission (optional - only admin can refresh)
            if not request.user.user_type.lower() in ['admin']:
                messages.error(request, "❌ Only admin users can refresh inventory cache.")
                return redirect('inventory_list')
            
            # Run cache rebuild in background thread
            def rebuild_cache_background():
                try:
                    print("🔄 Starting inventory cache rebuild...")
                    rebuild_all_cache()
                    print("✅ Inventory cache rebuild completed!")
                except Exception as e:
                    print(f"❌ Cache rebuild error: {e}")
            
            # Start background thread
            thread = threading.Thread(target=rebuild_cache_background)
            thread.daemon = True
            thread.start()
            
            messages.success(request, "🔄 Inventory cache refresh started! This may take a few moments. Please refresh the page after 10-15 seconds.")
            
            # Handle AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Cache refresh started successfully!'
                })
            
            return redirect('inventory_list')
            
        except Exception as e:
            messages.error(request, f"❌ Error refreshing cache: {str(e)}")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            
            return redirect('inventory_list')
    
    # GET request - redirect to inventory list
    return redirect('inventory_list')


@login_required
def quick_refresh_inventory_cache(request):
    """
    Quick synchronous cache refresh (for small datasets)
    Use this if you have less than 500 products
    """
    if request.method == 'POST':
        try:
            if not request.user.user_type.lower() in ['admin']:
                return JsonResponse({
                    'success': False,
                    'error': 'Only admin users can refresh cache'
                })
            
            # Synchronous rebuild
            rebuild_all_cache()
            
            return JsonResponse({
                'success': True,
                'message': 'Cache refreshed successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'})
