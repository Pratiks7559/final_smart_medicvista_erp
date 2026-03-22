from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1014_merge_20251202_2140'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name='inventorymaster',
                    name='product',
                ),
                migrations.RemoveField(
                    model_name='inventorymaster',
                    name='supplier',
                ),
                migrations.RemoveField(
                    model_name='inventorytransaction',
                    name='inventory',
                ),
                migrations.RemoveField(
                    model_name='inventorytransaction',
                    name='created_by',
                ),
                migrations.DeleteModel(
                    name='BatchStockSummary',
                ),
                migrations.DeleteModel(
                    name='InventoryMaster',
                ),
                migrations.DeleteModel(
                    name='InventoryTransaction',
                ),
            ],
        ),
    ]
