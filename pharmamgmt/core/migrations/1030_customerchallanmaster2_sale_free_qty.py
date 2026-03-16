from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1029_customerchallanmaster_sale_free_qty_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerchallanmaster2',
            name='sale_free_qty',
            field=models.FloatField(default=0.0, help_text='Free quantity given'),
        ),
    ]
