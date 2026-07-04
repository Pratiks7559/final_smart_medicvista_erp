from django.urls import path
from .retailer_views import (
    retailer_report_requests,
    api_pending_requests,
    api_update_status,
    api_health_check,
    api_request_data,
    api_upload_csv,
    api_report_failed,
    api_retailer_status,
    api_retailer_products,
    retailer_uploads_list,
    retailer_upload_preview,
    retailer_upload_download,
    retailer_uploads_download_zip,
    api_delete_request,
    api_deleted_request_ids,
)

urlpatterns = [
    # Wholesaler UI
    path('retailer-reports/', retailer_report_requests, name='retailer_report_requests'),
    path('retailer-reports/<int:request_id>/delete/', api_delete_request, name='retailer_report_request_delete'),

    # CSV Upload list & preview
    path('wholesaler/retailer-uploads/', retailer_uploads_list, name='retailer_uploads_list'),
    path('wholesaler/retailer-uploads/<int:upload_id>/preview/', retailer_upload_preview, name='retailer_upload_preview'),
    path('wholesaler/retailer-uploads/<int:upload_id>/download/', retailer_upload_download, name='retailer_upload_download'),
    path('wholesaler/retailer-uploads/download-zip/', retailer_uploads_download_zip, name='retailer_uploads_download_zip'),

    # Retailer REST API
    path('api/retailer/health/',               api_health_check,        name='api_retailer_health'),
    path('api/retailer/pending-requests/',     api_pending_requests,    name='api_retailer_pending_requests'),
    path('api/retailer/request-data/<int:request_id>/', api_request_data, name='api_retailer_request_data'),
    path('api/retailer/update-status/',        api_update_status,       name='api_retailer_update_status'),
    path('api/retailer/upload-csv/',           api_upload_csv,          name='api_retailer_upload_csv'),
    path('api/retailer/report-failed/',        api_report_failed,       name='api_retailer_report_failed'),
    path('api/retailer/status/',               api_retailer_status,     name='api_retailer_status'),
    path('api/retailer/products/',             api_retailer_products,   name='api_retailer_products'),
    path('api/retailer/deleted-request-ids/', api_deleted_request_ids, name='api_retailer_deleted_request_ids'),
]
