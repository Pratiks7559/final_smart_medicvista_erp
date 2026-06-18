from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1039_add_retailer_csv_upload'),
    ]

    operations = [
        migrations.CreateModel(
            name='RetailerSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_online', models.BooleanField(default=False)),
                ('last_login', models.DateTimeField(blank=True, null=True)),
                ('last_logout', models.DateTimeField(blank=True, null=True)),
                ('retailer', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='session',
                    to='core.retailermaster',
                )),
            ],
        ),
    ]
