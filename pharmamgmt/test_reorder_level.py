"""
Test script for Reorder Level calculation — matches reorder_level_views.py exactly
Run this from Django shell: python manage.py shell < test_reorder_level.py
"""

from datetime import datetime, timedelta
from django.db.models import Sum, Q
from core.models import ProductMaster, SalesMaster, BatchInventoryCache

# Must match constants in reorder_level_views.py
ANALYSIS_DAYS  = 90
LEAD_TIME_DAYS = 30


def test_reorder_level_calculation():
    """Test reorder level calculation — same formula as reorder_level_views.py"""

    print("=" * 60)
    print("REORDER LEVEL CALCULATION TEST")
    print(f"Sales window: {ANALYSIS_DAYS} days | Lead time: {LEAD_TIME_DAYS} days")
    print("=" * 60)

    analysis_start = datetime.now() - timedelta(days=ANALYSIS_DAYS)

    # Search for 1st Aid product; fallback to first 5 products
    products = ProductMaster.objects.filter(
        Q(product_name__icontains='1st aid') | Q(product_name__icontains='first aid')
    )
    if not products.exists():
        print("No '1st Aid' product found — showing first 5 products instead")
        products = ProductMaster.objects.all()[:5]

    for product in products:
        print(f"\n📦 Product: {product.product_name}")
        print(f"   Company: {product.product_company}")
        print("-" * 60)

        sales_qty = SalesMaster.objects.filter(
            productid=product,
            sale_entry_date__gte=analysis_start
        ).aggregate(total=Sum('sale_quantity'))['total'] or 0

        total_sales      = float(sales_qty)
        avg_daily_sale   = total_sales / ANALYSIS_DAYS
        avg_monthly_sale = round(avg_daily_sale * 30, 2)
        reorder_level    = round(avg_daily_sale * LEAD_TIME_DAYS, 2)

        print(f"📊 Sales (Last {ANALYSIS_DAYS} days): {total_sales:.2f} units")
        print(f"📈 Avg Daily Sale: {avg_daily_sale:.4f} units")
        print(f"📈 Avg Monthly Sale (display): {avg_monthly_sale:.2f} units")
        print(f"🎯 Reorder Level (avg_daily x {LEAD_TIME_DAYS}): {reorder_level:.2f} units")

        batches = BatchInventoryCache.objects.filter(
            product=product,
            current_stock__gt=0
        ).order_by('expiry_date', 'batch_no')

        total_available = 0.0
        for batch in batches:
            stock = float(batch.current_stock)  # free_qty excluded — same as views.py
            total_available += stock
            print(f"   Batch {batch.batch_no}: stock={stock:.2f}, free_qty={float(batch.current_free_qty):.2f} (Exp: {batch.expiry_date})")

        total_available = round(total_available, 2)
        reorder_needed  = round(max(0.0, reorder_level - total_available), 2)

        print(f"📦 Total Available Stock (free_qty excluded): {total_available:.2f} units")

        if reorder_needed > 0:
            print("🔴 CRITICAL - REORDER NEEDED")
            print(f"🛒 Order Quantity: {reorder_needed:.2f} units")
        else:
            surplus = round(total_available - reorder_level, 2)
            print("🟢 SUFFICIENT")
            print(f"✅ Stock is adequate (Surplus: {surplus:.2f})")

        print("=" * 60)

    print("\n✅ Test completed successfully!")
    print(f"\nFormula: reorder_level = (total_sales_{ANALYSIS_DAYS}d / {ANALYSIS_DAYS}) x {LEAD_TIME_DAYS}")
    print("        reorder_needed = max(0, reorder_level - total_available)")
    print("Note: free_qty is NOT counted in total_available (matches views.py)")


if __name__ == "__main__":
    test_reorder_level_calculation()
