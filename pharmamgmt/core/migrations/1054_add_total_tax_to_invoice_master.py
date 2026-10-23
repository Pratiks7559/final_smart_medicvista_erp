from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1053_remove_invoicemaster_unique_supplier_invoice_fy'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicemaster',
            name='total_tax',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]
