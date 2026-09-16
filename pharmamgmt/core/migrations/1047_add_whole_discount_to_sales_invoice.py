from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1046_supplieradvance_customeradvance_advanceledger'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoicemaster',
            name='whole_discount_amount',
            field=models.FloatField(default=0),
        ),
    ]
