"""
Cleanup script to remove duplicate inventory transactions
Run this once to clean existing duplicates
"""
from django.db.models import Count
from core.models import InventoryTransaction

def cleanup_duplicate_transactions():
    """Remove duplicate transactions keeping only the latest one"""
    
    stats = {
        'duplicates_found': 0,
        'duplicates_removed': 0,
        'errors': 0
    }
    
    # Find duplicates based on: product, batch_no, reference_type, reference_id, transaction_type
    duplicates = InventoryTransaction.objects.values(
        'product_id', 'batch_no', 'reference_type', 'reference_id', 'transaction_type'
    ).annotate(
        count=Count('transaction_id')
    ).filter(count__gt=1)
    
    print(f"Found {duplicates.count()} groups with duplicate transactions")
    stats['duplicates_found'] = duplicates.count()
    
    for dup in duplicates:
        try:
            # Get all transactions in this duplicate group
            transactions = InventoryTransaction.objects.filter(
                product_id=dup['product_id'],
                batch_no=dup['batch_no'],
                reference_type=dup['reference_type'],
                reference_id=dup['reference_id'],
                transaction_type=dup['transaction_type']
            ).order_by('-created_at')  # Latest first
            
            # Keep the first (latest) one, delete the rest
            keep_txn = transactions.first()
            delete_txns = transactions.exclude(transaction_id=keep_txn.transaction_id)
            
            count = delete_txns.count()
            delete_txns.delete()
            
            stats['duplicates_removed'] += count
            print(f"Removed {count} duplicate(s) for {keep_txn.product.product_name} - Batch {keep_txn.batch_no}")
            
        except Exception as e:
            stats['errors'] += 1
            print(f"Error cleaning duplicate: {e}")
    
    print("\n=== Cleanup Summary ===")
    print(f"Duplicate groups found: {stats['duplicates_found']}")
    print(f"Duplicate transactions removed: {stats['duplicates_removed']}")
    print(f"Errors: {stats['errors']}")
    
    return stats


if __name__ == '__main__':
    cleanup_duplicate_transactions()
