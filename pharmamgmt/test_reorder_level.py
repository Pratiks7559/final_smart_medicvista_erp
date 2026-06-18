"""
Test script for Reorder Level calculation
Run this from Django shell: python manage.py shell < test_reorder_level.py
"""

from datetime import datetime, timedelta
from django.db.models import Sum
from core.models import ProductMaster, SalesMaster, BatchInventoryCache

def test_reorder_level_calculation():
    """Test reorder level calculation for a sample product"""
    
    print("=" * 60)
    print("REORDER LEVEL CALCULATION TEST")
    print("=" * 60)
    
    # Get first product with sales and stock
    products = ProductMaster.objects.all()[:5]
    
    for product in products:
        print(f"\n📦 Product: {product.product_name}")
        print(f"   Company: {product.product_company}")
        print("-" * 60)
        
        # Calculate sales (last 30 days)
        thirty_days_ago = datetime.now() - timedelta(days=30)
        sales_qty = SalesMaster.objects.filter(
            productid=product,
            sale_entry_date__gte=thirty_days_ago
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0
        
        avg_monthly_sale = float(sales_qty)
        reorder_level_qty = avg_monthly_sale * 1.5
        
        print(f"📊 Sales (Last 30 days): {avg_monthly_sale:.2f} units")
        print(f"📈 Reorder Level (1.5x): {reorder_level_qty:.2f} units")
        
        # Get available stock
        batches = BatchInventoryCache.objects.filter(
            product=product,
            current_stock__gt=0
        )
        
        total_available = 0
        batch_count = 0
        
        for batch in batches:
            batch_stock = float(batch.current_stock) + float(batch.current_free_qty)
            total_available += batch_stock
            batch_count += 1
            print(f"   Batch {batch.batch_no}: {batch_stock:.2f} (Exp: {batch.expiry_date})")
        
        print(f"📦 Total Available Stock: {total_available:.2f} units ({batch_count} batches)")
        
        # Calculate reorder needed
        reorder_needed = max(0, reorder_level_qty - total_available)
        
        if reorder_needed > 0:
            status = "🔴 CRITICAL - REORDER NEEDED"
            print(f"{status}")
            print(f"🛒 Order Quantity: {reorder_needed:.2f} units")
        else:
            status = "🟢 SUFFICIENT"
            print(f"{status}")
            print(f"✅ Stock is adequate (Surplus: {abs(reorder_needed):.2f})")
        
        print("=" * 60)
    
    print("\n✅ Test completed successfully!")
    print("\nFormula: Reorder Level = (Avg Monthly Sale × 1.5) - Available Stock")
    print("Note: Last 30 days sales data used for calculation")

if __name__ == "__main__":
    test_reorder_level_calculation()
