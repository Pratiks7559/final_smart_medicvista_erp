from django.db import migrations, models


def populate_invoice_financial_year(apps, schema_editor):
    InvoiceMaster = apps.get_model('core', 'InvoiceMaster')
    invoices = InvoiceMaster.objects.only('invoiceid', 'invoice_date').iterator()
    for invoice in invoices:
        invoice.invoice_financial_year = (
            invoice.invoice_date.year
            if invoice.invoice_date.month >= 4
            else invoice.invoice_date.year - 1
        )
        invoice.save(update_fields=['invoice_financial_year'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1050_add_whole_discount_to_invoice_master'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicemaster',
            name='invoice_financial_year',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(
            populate_invoice_financial_year,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='invoicemaster',
            name='invoice_financial_year',
            field=models.PositiveIntegerField(),
        ),
        migrations.RemoveConstraint(
            model_name='invoicemaster',
            name='unique_invoiceno_supplierid',
        ),
        migrations.AddConstraint(
            model_name='invoicemaster',
            constraint=models.UniqueConstraint(
                fields=('invoice_no', 'supplierid', 'invoice_financial_year'),
                name='unique_supplier_invoice_fy',
            ),
        ),
    ]
