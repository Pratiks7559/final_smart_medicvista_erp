from core.models import InventoryTransaction
from django.db.models import Sum, Count

print('='*60)
print('INVENTORY TRANSACTION VERIFICATION')
print('='*60)

# Total transactions
total = InventoryTransaction.objects.count()
print(f'\nTotal Transactions: {total}')

# By transaction type
print('\nTransactions by Type:')
types = InventoryTransaction.objects.values('transaction_type').annotate(
    count=Count('transaction_id'),
    total_qty=Sum('quantity')
).order_by('transaction_type')

for t in types:
    print(f"  {t['transaction_type']}: {t['count']} transactions, Total Qty: {t['total_qty']}")

# Sample transactions
print('\nSample Transactions (First 5):')
for txn in InventoryTransaction.objects.all()[:5]:
    print(f"  {txn.transaction_type} - {txn.product.product_name} - Batch: {txn.batch_no} - Qty: {txn.quantity}")

# Stock calculation test
print('\nStock Calculation Test:')
if total > 0:
    first_txn = InventoryTransaction.objects.first()
    stock = InventoryTransaction.get_batch_stock(
        product_id=first_txn.product_id,
        batch_no=first_txn.batch_no
    )
    print(f"  Product: {first_txn.product.product_name}")
    print(f"  Batch: {first_txn.batch_no}")
    print(f"  Stock: {stock['stock']}")
    print(f"  Free Stock: {stock['free_stock']}")
    print(f"  Total Stock: {stock['total_stock']}")

print('\n' + '='*60)
print('VERIFICATION COMPLETE!')
print('='*60)
