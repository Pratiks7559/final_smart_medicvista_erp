from django.urls import path
from .retailer_views import (
    retailer_report_requests,
    api_pending_requests,
    api_update_status,
    api_health_check,
    api_request_data,
)

urlpatterns = [
    # Wholesaler UI
    path('retailer-reports/', retailer_report_requests, name='retailer_report_requests'),

    # Retailer REST API
    path('api/retailer/health/', api_health_check, name='api_retailer_health'),
    path('api/retailer/pending-requests/', api_pending_requests, name='api_retailer_pending_requests'),
    path('api/retailer/request-data/<int:request_id>/', api_request_data, name='api_retailer_request_data'),
    path('api/retailer/update-status/', api_update_status, name='api_retailer_update_status'),
]
