from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1037_alter_productmaster_product_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='RetailerMaster',
            fields=[
                ('retailer_id', models.AutoField(primary_key=True, serialize=False)),
                ('retailer_name', models.CharField(max_length=200)),
                ('retailer_code', models.CharField(max_length=50, unique=True)),
                ('api_key', models.CharField(default=uuid.uuid4, max_length=64, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.CreateModel(
            name='RetailerReportRequest',
            fields=[
                ('request_id', models.AutoField(primary_key=True, serialize=False)),
                ('retailer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='core.retailermaster')),
                ('request_type', models.CharField(choices=[('STOCK', 'Stock'), ('PURCHASE', 'Purchase'), ('SALES', 'Sales')], max_length=10)),
                ('from_date', models.DateField()),
                ('to_date', models.DateField()),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PROCESSING', 'Processing'), ('COMPLETED', 'Completed'), ('FAILED', 'Failed')], default='PENDING', max_length=15)),
                ('created_by', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('remarks', models.TextField(blank=True, default='')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
