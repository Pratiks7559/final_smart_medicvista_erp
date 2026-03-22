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
        ('core', '0010_alter_salesmaster_id'),
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
            create_index_if_not_exists('idx_product_barcode', 'core_productmaster', 'product_barcode'),
            drop_index_if_exists('idx_product_barcode', 'core_productmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_productid', 'core_purchasemaster', 'productid_id'),
            drop_index_if_exists('idx_purchase_productid', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_batch', 'core_purchasemaster', 'product_batch_no'),
            drop_index_if_exists('idx_purchase_batch', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_expiry', 'core_purchasemaster', 'product_expiry'),
            drop_index_if_exists('idx_purchase_expiry', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_sales_productid', 'core_salesmaster', 'productid_id'),
            drop_index_if_exists('idx_sales_productid', 'core_salesmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_sales_batch', 'core_salesmaster', 'product_batch_no'),
            drop_index_if_exists('idx_sales_batch', 'core_salesmaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_purchase_product_batch', 'core_purchasemaster', 'productid_id, product_batch_no'),
            drop_index_if_exists('idx_purchase_product_batch', 'core_purchasemaster'),
        ),
        migrations.RunPython(
            create_index_if_not_exists('idx_sales_product_batch', 'core_salesmaster', 'productid_id, product_batch_no'),
            drop_index_if_exists('idx_sales_product_batch', 'core_salesmaster'),
        ),
    ]
