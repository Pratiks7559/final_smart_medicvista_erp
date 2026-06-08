from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class LoginRequiredMiddleware:
    """
    Middleware to ensure user is authenticated for all views except login/logout
    """
    def __init__(self, get_response):
        self.get_response = get_response
        # URLs that don't require authentication
        self.exempt_urls = [
            reverse('landing_page'),
            reverse('login'),
            reverse('logout'),
            '/admin/login/',
            '/static/',
            '/media/',
            '/api/retailer/',   # API key auth — no session needed
        ]
    
    def __call__(self, request):
        # Check if user is authenticated
        if not request.user.is_authenticated:
            # Check if current path is exempt
            path = request.path_info
            
            # Allow exempt URLs
            if any(path.startswith(url) for url in self.exempt_urls):
                return self.get_response(request)
            
            # Redirect to login page
            login_url = settings.LOGIN_URL
            return redirect(f'{login_url}?next={path}')
        
        return self.get_response(request)
