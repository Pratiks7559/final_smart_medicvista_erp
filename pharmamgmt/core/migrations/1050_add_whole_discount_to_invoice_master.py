from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1049_add_whole_discount_to_customer_challan'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicemaster',
            name='whole_discount_amount',
            field=models.FloatField(default=0.0),
        ),
    ]
