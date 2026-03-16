# Generated migration to add product_free_qty field to SupplierChallanMaster2

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_add_finance_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplierchallanmaster2',
            name='product_free_qty',
            field=models.FloatField(default=0.0),
        ),
    ]
