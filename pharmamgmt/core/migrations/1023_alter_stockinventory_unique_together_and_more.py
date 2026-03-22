from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1022_add_inventory_performance_indexes'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterUniqueTogether(
                    name='stockinventory',
                    unique_together=None,
                ),
                migrations.RemoveField(
                    model_name='stockinventory',
                    name='product',
                ),
                migrations.RemoveIndex(
                    model_name='customerchallanmaster',
                    name='idx_cust_chal_prod_batch',
                ),
                migrations.RemoveIndex(
                    model_name='purchasemaster',
                    name='idx_purchase_prod_batch',
                ),
                migrations.RemoveIndex(
                    model_name='purchasemaster',
                    name='idx_purchase_invoice',
                ),
                migrations.RemoveIndex(
                    model_name='returnpurchasemaster',
                    name='idx_ret_pur_prod_batch',
                ),
                migrations.RemoveIndex(
                    model_name='returnsalesmaster',
                    name='idx_ret_sal_prod_batch',
                ),
                migrations.RemoveIndex(
                    model_name='salesmaster',
                    name='idx_sales_prod_batch',
                ),
                migrations.RemoveIndex(
                    model_name='salesmaster',
                    name='idx_sales_invoice',
                ),
                migrations.RemoveIndex(
                    model_name='supplierchallanmaster',
                    name='idx_sup_chal_prod_batch',
                ),
                migrations.DeleteModel(
                    name='StockInventory',
                ),
            ],
        ),
    ]
