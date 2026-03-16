from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1030_customerchallanmaster2_sale_free_qty'),
    ]

    operations = [
        migrations.AddField(
            model_name='returnpurchasemaster',
            name='returnproduct_free_qty',
            field=models.FloatField(default=0.0, help_text='Free quantity returned'),
        ),
    ]
