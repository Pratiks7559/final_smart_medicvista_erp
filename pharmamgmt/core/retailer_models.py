import uuid
from django.db import models
from django.utils import timezone
import logging

logger = logging.getLogger('retailer_sync')


class RetailerSession(models.Model):
    """Tracks real-time online/offline status of each retailer via last health check."""
    retailer   = models.OneToOneField(
        'RetailerMaster', on_delete=models.CASCADE, related_name='session'
    )
    is_online  = models.BooleanField(default=False)
    last_seen  = models.DateTimeField(null=True, blank=True)
    last_login  = models.DateTimeField(null=True, blank=True)
    last_logout = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        status = 'Online' if self.is_online else 'Offline'
        return f"{self.retailer.retailer_name} — {status}"


class RetailerMaster(models.Model):
    retailer_id = models.AutoField(primary_key=True)
    retailer_name = models.CharField(max_length=200)
    retailer_code = models.CharField(max_length=50, unique=True)
    api_key = models.CharField(max_length=64, unique=True, default=uuid.uuid4)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.retailer_name} ({self.retailer_code})"


class RetailerReportRequest(models.Model):
    REPORT_TYPE_CHOICES = [
        ('STOCK',    'Stock'),
        ('PURCHASE', 'Purchase'),
        ('SALES',    'Sales'),
        ('RETURN',   'Return'),
    ]
    STATUS_CHOICES = [
        ('PENDING',    'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED',  'Completed'),
        ('FAILED',     'Failed'),
    ]

    request_id    = models.AutoField(primary_key=True)
    retailer      = models.ForeignKey(RetailerMaster, on_delete=models.CASCADE)
    request_type  = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    from_date     = models.DateField()
    to_date       = models.DateField()
    status        = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_by    = models.CharField(max_length=150)
    created_at    = models.DateTimeField(default=timezone.now)
    completed_at  = models.DateTimeField(null=True, blank=True)
    remarks       = models.TextField(blank=True, default='')
    error_message = models.TextField(blank=True, default='')
    product_ids   = models.TextField(blank=True, default='')  # comma-separated product IDs, empty = all products

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request #{self.request_id} - {self.retailer} - {self.request_type}"


class RetailerCSVUpload(models.Model):
    REPORT_TYPE_CHOICES = [
        ('STOCK',    'Stock'),
        ('PURCHASE', 'Purchase'),
        ('SALES',    'Sales'),
        ('RETURN',   'Return'),
    ]

    request      = models.ForeignKey(RetailerReportRequest, on_delete=models.CASCADE, related_name='csv_uploads')
    retailer     = models.ForeignKey(RetailerMaster, on_delete=models.CASCADE, related_name='csv_uploads')
    csv_file     = models.FileField(upload_to='retailer_csv_uploads/%Y/%m/')
    file_name    = models.CharField(max_length=255)
    file_size_kb = models.FloatField(default=0)
    request_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    uploaded_at  = models.DateTimeField(auto_now_add=True)
    row_count    = models.IntegerField(default=0)
    preview_data = models.JSONField(null=True, blank=True)
    generated_by = models.CharField(max_length=100, blank=True, default='')  # retailer_code

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.retailer.retailer_code} | {self.request_type} | {self.file_name}"
