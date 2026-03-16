from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1031_returnpurchasemaster_returnproduct_free_qty'),
    ]

    operations = [
        migrations.AddField(
            model_name='returnsalesmaster',
            name='return_sale_free_qty',
            field=models.FloatField(default=0.0, help_text='Free quantity returned'),
        ),
    ]
