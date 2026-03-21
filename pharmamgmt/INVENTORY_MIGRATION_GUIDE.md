# Inventory Transaction Migration Guide

## Overview
Ye migration script aapke purane data ko naye InventoryTransaction system mein migrate karega.

## Kya Migrate Hoga?

### 1. Purchase Data (PurchaseMaster)
- ✅ Product quantity (IN - Positive)
- ✅ Free quantity (IN - Positive)
- ✅ Batch number, Expiry date
- ✅ Purchase rate, MRP
- ✅ Invoice reference

### 2. Sales Data (SalesMaster)
- ✅ Sale quantity (OUT - Negative)
- ✅ Free quantity (OUT - Negative)
- ✅ Batch number, Expiry date
- ✅ Sale rate, MRP
- ✅ Invoice reference

### 3. Purchase Returns (ReturnPurchaseMaster)
- ✅ Return quantity (OUT - Negative)
- ✅ Free quantity (OUT - Negative)
- ✅ Return invoice reference

### 4. Sales Returns (ReturnSalesMaster)
- ✅ Return quantity (IN - Positive)
- ✅ Free quantity (IN - Positive)
- ✅ Return invoice reference

### 5. Supplier Challans (SupplierChallanMaster)
- ✅ Challan quantity (IN - Positive)
- ✅ Free quantity (IN - Positive)
- ✅ Challan reference

### 6. Customer Challans (CustomerChallanMaster)
- ✅ Challan quantity (OUT - Negative)
- ✅ Free quantity (OUT - Negative)
- ✅ Challan reference

### 7. Stock Issues (StockIssueDetail)
- ✅ Issue quantity (OUT - Negative)
- ✅ Issue type (damage, expiry, etc.)
- ✅ Issue reference

## Migration Steps

### Step 1: Backup Database
```bash
# IMPORTANT: Backup your database first!
cd c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService\pharmamgmt
python manage.py dumpdata > backup_before_migration.json
```

### Step 2: Run Migration (First Time)
```bash
# Migrate all existing data
python manage.py migrate_inventory_transactions
```

### Step 3: Verify Data
```bash
# Check if migration was successful
# Script will show summary:
# - Total purchases migrated
# - Total sales migrated
# - Total returns migrated
# - Top 5 products by stock
```

### Step 4: Re-run if Needed (Clear & Migrate)
```bash
# If you need to re-run migration (clears existing transactions first)
python manage.py migrate_inventory_transactions --clear
```

## Migration Logic

### Stock IN (Positive Quantity):
- ✅ Purchases
- ✅ Sales Returns
- ✅ Supplier Challans

### Stock OUT (Negative Quantity):
- ✅ Sales
- ✅ Purchase Returns
- ✅ Customer Challans
- ✅ Stock Issues

## Expected Output

```
Starting Inventory Transaction Migration...

1. Migrating Purchase Data...
  Processed 100 purchases...
  Processed 200 purchases...
✓ Migrated 250 purchases

2. Migrating Sales Data...
  Processed 100 sales...
  Processed 200 sales...
✓ Migrated 300 sales

3. Migrating Purchase Returns...
✓ Migrated 15 purchase returns

4. Migrating Sales Returns...
✓ Migrated 20 sales returns

5. Migrating Supplier Challans...
✓ Migrated 50 supplier challans

6. Migrating Customer Challans...
✓ Migrated 40 customer challans

7. Migrating Stock Issues...
✓ Migrated 10 stock issues

============================================================
MIGRATION SUMMARY
============================================================
✓ Purchases:          250
✓ Sales:              300
✓ Purchase Returns:   15
✓ Sales Returns:      20
✓ Supplier Challans:  50
✓ Customer Challans:  40
✓ Stock Issues:       10
------------------------------------------------------------
TOTAL MIGRATED:       685
============================================================

✓ Migration completed successfully!

============================================================
VERIFICATION
============================================================
Total Inventory Transactions: 685

Top 5 Products by Stock:
1. Paracetamol 500mg: 1500
2. Amoxicillin 250mg: 1200
3. Cetirizine 10mg: 800
4. Azithromycin 500mg: 600
5. Metformin 500mg: 500

============================================================
```

## Troubleshooting

### Error: "No module named 'core.management'"
**Solution**: Make sure __init__.py files exist:
```bash
# Create __init__.py files
echo. > core\management\__init__.py
echo. > core\management\commands\__init__.py
```

### Error: "Duplicate transactions"
**Solution**: Clear and re-run:
```bash
python manage.py migrate_inventory_transactions --clear
```

### Error: "Invalid expiry date format"
**Solution**: Script handles both date formats:
- MM-YYYY (string)
- Date object

### Stock Balance Mismatch
**Solution**: 
1. Check if all transactions migrated
2. Verify transaction types (IN vs OUT)
3. Check for duplicate entries

## Post-Migration Checks

### 1. Verify Stock Counts
```python
# Run in Django shell
python manage.py shell

from core.models import InventoryTransaction
from django.db.models import Sum

# Check total stock for a product
product_id = 1
stock = InventoryTransaction.objects.filter(
    product_id=product_id
).aggregate(
    total=Sum('quantity')
)
print(f"Total Stock: {stock['total']}")
```

### 2. Compare with Old System
- Check inventory list 1 (cached)
- Check inventory list 2 (real-time)
- Compare stock values
- Verify batch-wise stock

### 3. Test Transaction History
- Open any product
- View transaction history
- Verify all transactions visible
- Check running balance

## Important Notes

### ⚠️ Before Migration:
1. ✅ Backup database
2. ✅ Test on staging/development first
3. ✅ Verify all data is correct
4. ✅ Inform users about maintenance

### ✅ After Migration:
1. ✅ Verify stock counts
2. ✅ Test inventory list 2
3. ✅ Check transaction history
4. ✅ Compare with old reports
5. ✅ Monitor for any issues

### 🔄 Future Transactions:
- New purchases will auto-create transactions (via signals)
- New sales will auto-create transactions (via signals)
- No manual intervention needed
- Real-time stock updates

## Migration Time Estimate

| Records | Estimated Time |
|---------|----------------|
| 1,000   | 30 seconds     |
| 10,000  | 3-5 minutes    |
| 50,000  | 15-20 minutes  |
| 100,000 | 30-40 minutes  |

## Support

If you face any issues:
1. Check error messages in console
2. Verify database backup exists
3. Check Django logs
4. Contact support with error details

## Rollback Plan

If migration fails:
```bash
# Restore from backup
python manage.py flush --no-input
python manage.py loaddata backup_before_migration.json
```

## Success Criteria

Migration is successful when:
- ✅ All transactions migrated without errors
- ✅ Stock counts match old system
- ✅ Transaction history shows all records
- ✅ Inventory List 2 displays correct data
- ✅ No duplicate transactions
- ✅ Running balance is correct

## Next Steps After Migration

1. **Test Thoroughly**
   - Create test purchase
   - Create test sale
   - Verify stock updates

2. **Monitor Performance**
   - Check page load times
   - Verify query performance
   - Monitor database size

3. **Train Users**
   - Show new inventory list 2
   - Explain transaction history
   - Demonstrate real-time updates

4. **Disable Old System** (Optional)
   - Keep old data for reference
   - Use new system for all operations
   - Archive old reports

## Conclusion

Ye migration script aapke saare purane data ko safely naye system mein migrate kar dega. 
Migration ke baad aapka inventory tracking real-time aur accurate ho jayega!

Good luck! 🚀
