from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1055_add_total_tax_to_challan1'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoicemaster',
            name='total_tax',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
        migrations.AddField(
            model_name='customerchallan',
            name='total_tax',
            field=models.FloatField(blank=True, default=None, null=True),
        ),
    ]
