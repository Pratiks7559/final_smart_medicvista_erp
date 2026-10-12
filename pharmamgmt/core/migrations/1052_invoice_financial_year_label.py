from django.db import migrations, models


def convert_invoice_financial_year_labels(apps, schema_editor):
    InvoiceMaster = apps.get_model('core', 'InvoiceMaster')
    for invoice in InvoiceMaster.objects.only('invoiceid', 'invoice_date').iterator():
        start_year = (
            invoice.invoice_date.year
            if invoice.invoice_date.month >= 4
            else invoice.invoice_date.year - 1
        )
        invoice.invoice_financial_year = f'{start_year}-{(start_year + 1) % 100:02d}'
        invoice.save(update_fields=['invoice_financial_year'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1051_invoice_number_unique_per_financial_year'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='invoicemaster',
            name='unique_supplier_invoice_fy',
        ),
        migrations.AlterField(
            model_name='invoicemaster',
            name='invoice_financial_year',
            field=models.CharField(max_length=7),
        ),
        migrations.RunPython(
            convert_invoice_financial_year_labels,
            migrations.RunPython.noop,
        ),
        migrations.AddConstraint(
            model_name='invoicemaster',
            constraint=models.UniqueConstraint(
                fields=('invoice_no', 'supplierid', 'invoice_financial_year'),
                name='unique_supplier_invoice_fy',
            ),
        ),
    ]
