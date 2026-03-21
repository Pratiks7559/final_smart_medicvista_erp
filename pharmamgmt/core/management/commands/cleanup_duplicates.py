from django.core.management.base import BaseCommand
from django.db.models import Count
from core.models import InventoryTransaction


class Command(BaseCommand):
    help = 'Cleanup duplicate inventory transactions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Starting cleanup of duplicate transactions...'))
        
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
        
        self.stdout.write(f"Found {duplicates.count()} groups with duplicate transactions")
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
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Removed {count} duplicate(s) for {keep_txn.product.product_name} - Batch {keep_txn.batch_no}"
                    )
                )
                
            except Exception as e:
                stats['errors'] += 1
                self.stdout.write(self.style.ERROR(f"Error cleaning duplicate: {e}"))
        
        self.stdout.write(self.style.SUCCESS("\n=== Cleanup Summary ==="))
        self.stdout.write(f"Duplicate groups found: {stats['duplicates_found']}")
        self.stdout.write(f"Duplicate transactions removed: {stats['duplicates_removed']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        
        if stats['duplicates_removed'] > 0:
            self.stdout.write(self.style.SUCCESS('\nCleanup completed successfully!'))
        else:
            self.stdout.write(self.style.WARNING('\nNo duplicates found to clean.'))
