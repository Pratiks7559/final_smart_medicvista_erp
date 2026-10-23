from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1054_add_total_tax_to_invoice_master'),
    ]

    operations = [
        migrations.AddField(
            model_name='challan1',
            name='total_tax',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]
