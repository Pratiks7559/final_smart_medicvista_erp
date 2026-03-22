from django.db import migrations, connection


def create_index_if_not_exists(index_name, table, columns):
    def forward(apps, schema_editor):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s",
                [table, index_name]
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(f"CREATE INDEX {index_name} ON {table}({columns})")
    return forward


def drop_index_if_exists(index_name, table):
    def reverse(apps, schema_editor):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.statistics "
                "WHERE table_schema = DATABASE() AND table_name = %s AND index_name = %s",
                [table, index_name]
            )
            if cursor.fetchone()[0] > 0:
                cursor.execute(f"DROP INDEX {index_name} ON {table}")
    return reverse


class Migration(migrations.Migration):

    dependencies = [
        ('core', '1021_add_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(
            create_index_if_not_exists('idx_product_name', 'core_productmaster', 'product_name'),
            drop_index_if_exists('idx_product_name', 'core_productmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_product_company', 'core_productmaster', 'product_company'),
            drop_index_if_exists('idx_product_company', 'core_productmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_product_batch', 'core_purchasemaster', 'productid_id, product_batch_no'),
            drop_index_if_exists('idx_purchase_product_batch', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_expiry', 'core_purchasemaster', 'product_expiry'),
            drop_index_if_exists('idx_purchase_expiry', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_sales_product_batch', 'core_salesmaster', 'productid_id, product_batch_no'),
            drop_index_if_exists('idx_sales_product_batch', 'core_salesmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_salerate_product_batch', 'core_saleratemaster', 'productid_id, product_batch_no'),
            drop_index_if_exists('idx_salerate_product_batch', 'core_saleratemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_return_purchase_product_batch', 'core_returnpurchasemaster', 'returnproductid_id, returnproduct_batch_no'),
            drop_index_if_exists('idx_return_purchase_product_batch', 'core_returnpurchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_return_sales_product_batch', 'core_returnsalesmaster', 'return_productid_id, return_product_batch_no'),
            drop_index_if_exists('idx_return_sales_product_batch', 'core_returnsalesmaster'),
        ),
    ]
