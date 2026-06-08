import uuid
from django.db import models
from django.utils import timezone


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
        ('STOCK', 'Stock'),
        ('PURCHASE', 'Purchase'),
        ('SALES', 'Sales'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    request_id = models.AutoField(primary_key=True)
    retailer = models.ForeignKey(RetailerMaster, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    from_date = models.DateField()
    to_date = models.DateField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.CharField(max_length=150)
    created_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request #{self.request_id} - {self.retailer} - {self.request_type}"
