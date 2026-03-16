# Generated migration for adding free qty to batch inventory cache

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1033_add_free_qty_to_sales_return'),
    ]

    operations = [
        migrations.AddField(
            model_name='batchinventorycache',
            name='current_free_qty',
            field=models.FloatField(default=0, help_text='Current free quantity in stock'),
        ),
    ]
