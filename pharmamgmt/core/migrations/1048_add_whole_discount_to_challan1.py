from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1047_add_whole_discount_to_sales_invoice'),
    ]

    operations = [
        migrations.AddField(
            model_name='challan1',
            name='whole_discount_amount',
            field=models.FloatField(default=0.0),
        ),
    ]
