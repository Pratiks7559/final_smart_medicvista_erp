"""
Inventory Cache Management
Handles updating ProductInventoryCache and BatchInventoryCache tables
"""
from django.db.models import Sum, Avg, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import (
    ProductMaster, ProductInventoryCache, BatchInventoryCache,
    PurchaseMaster, SalesMaster, ReturnPurchaseMaster, ReturnSalesMaster,
    SupplierChallanMaster, CustomerChallanMaster,
    SaleRateMaster
)


def calculate_batch_stock(product_id, batch_no, expiry_date):
    """Calculate current stock for a specific batch - OPTIMIZED with all transactions"""
    # ⬆️ INCREASE: Purchase + Supplier Challan + Sales Return
    purchased = PurchaseMaster.objects.filter(
        productid=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).aggregate(total=Sum('product_quantity'))['total'] or 0
    
    purchased_free = PurchaseMaster.objects.filter(
        productid=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).aggregate(total=Sum('product_free_qty'))['total'] or 0
    
    # CRITICAL FIX: Only count SupplierChallanMaster entries that are NOT already in PurchaseMaster
    # Get challan numbers that are already invoiced (present in PurchaseMaster)
    invoiced_challan_nos = PurchaseMaster.objects.filter(
        productid=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date,
        source_challan_no__isnull=False
    ).values_list('source_challan_no', flat=True).distinct()
    
    # Only count challan entries that haven't been invoiced yet
    supplier_challan = SupplierChallanMaster.objects.filter(
        product_id=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).exclude(
        product_challan_no__in=invoiced_challan_nos
    ).aggregate(total=Sum('product_quantity'))['total'] or 0
    
    supplier_challan_free = SupplierChallanMaster.objects.filter(
        product_id=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).exclude(
        product_challan_no__in=invoiced_challan_nos
    ).aggregate(total=Sum('product_free_qty'))['total'] or 0
    
    sales_returns = ReturnSalesMaster.objects.filter(
        return_productid=product_id,
        return_product_batch_no=batch_no,
        return_product_expiry=expiry_date
    ).aggregate(total=Sum('return_sale_quantity'))['total'] or 0
    
    sales_returns_free = ReturnSalesMaster.objects.filter(
        return_productid=product_id,
        return_product_batch_no=batch_no,
        return_product_expiry=expiry_date
    ).aggregate(total=Sum('return_sale_free_qty'))['total'] or 0
    
    # ⬇️ DECREASE: Sales + Customer Challan + Purchase Return
    sold = SalesMaster.objects.filter(
        productid=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).aggregate(total=Sum('sale_quantity'))['total'] or 0
    
    sold_free = SalesMaster.objects.filter(
        productid=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).aggregate(total=Sum('sale_free_qty'))['total'] or 0
    
    customer_challan = CustomerChallanMaster.objects.filter(
        product_id=product_id,
        product_batch_no=batch_no,
        product_expiry=expiry_date
    ).aggregate(total=Sum('sale_quantity'))['total'] or 0
    
    purchase_returns = ReturnPurchaseMaster.objects.filter(
        returnproductid=product_id,
        returnproduct_batch_no=batch_no
    ).aggregate(total=Sum('returnproduct_quantity'))['total'] or 0
    
    purchase_returns_free = ReturnPurchaseMaster.objects.filter(
        returnproductid=product_id,
        returnproduct_batch_no=batch_no
    ).aggregate(total=Sum('returnproduct_free_qty'))['total'] or 0
    
    # Calculate: INCREASE - DECREASE
    current_stock = (purchased + supplier_challan + sales_returns) - (sold + customer_challan + purchase_returns)
    current_free_qty = (purchased_free + supplier_challan_free + sales_returns_free) - (sold_free + purchase_returns_free)
    
    return max(0, current_stock), max(0, current_free_qty)


def check_expiry_status(expiry_str):
    """Check if batch is expired or expiring soon"""
    if not expiry_str:
        return 'valid', False
    
    try:
        # Parse MM-YYYY format
        month, year = map(int, expiry_str.split('-'))
        expiry_date = datetime(year, month, 1)
        
        # Get last day of month
        if month == 12:
            expiry_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            expiry_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        current_date = datetime.now()
        days_to_expiry = (expiry_date - current_date).days
        
        if days_to_expiry < 0:
            return 'expired', True
        elif days_to_expiry <= 90:  # 3 months
            return 'expiring_soon', False
        else:
            return 'valid', False
    except:
        return 'valid', False


def update_batch_cache(product_id, batch_no, expiry_date):
    """Update cache for a specific batch"""
    try:
        # Calculate stock and free qty
        current_stock, current_free_qty = calculate_batch_stock(product_id, batch_no, expiry_date)
        
        # If no stock and no source records exist, delete the cache entry
        if current_stock <= 0:
            purchase_exists = PurchaseMaster.objects.filter(
                productid=product_id,
                product_batch_no=batch_no,
                product_expiry=expiry_date
            ).exists()
            
            challan_exists = SupplierChallanMaster.objects.filter(
                product_id=product_id,
                product_batch_no=batch_no,
                product_expiry=expiry_date
            ).exists()
            
            if not purchase_exists and not challan_exists:
                # No source records, delete cache
                BatchInventoryCache.objects.filter(
                    product_id=product_id,
                    batch_no=batch_no,
                    expiry_date=expiry_date
                ).delete()
                return None
        
        # Get batch details from first purchase
        purchase = PurchaseMaster.objects.filter(
            productid=product_id,
            product_batch_no=batch_no,
            product_expiry=expiry_date
        ).first()
        
        if not purchase:
            # Try challan
            challan = SupplierChallanMaster.objects.filter(
                product_id=product_id,
                product_batch_no=batch_no,
                product_expiry=expiry_date
            ).first()
            
            if challan:
                mrp = challan.product_mrp
                purchase_rate = challan.product_purchase_rate
                rate_a = challan.rate_a
                rate_b = challan.rate_b
                rate_c = challan.rate_c
            else:
                # No source found, delete cache if exists
                BatchInventoryCache.objects.filter(
                    product_id=product_id,
                    batch_no=batch_no,
                    expiry_date=expiry_date
                ).delete()
                return None
        else:
            mrp = purchase.product_MRP
            purchase_rate = purchase.product_purchase_rate
            rate_a = purchase.rate_a
            rate_b = purchase.rate_b
            rate_c = purchase.rate_c
        
        # Get rates from SaleRateMaster if available
        try:
            sale_rate = SaleRateMaster.objects.get(
                productid=product_id,
                product_batch_no=batch_no
            )
            rate_a = sale_rate.rate_A
            rate_b = sale_rate.rate_B
            rate_c = sale_rate.rate_C
        except SaleRateMaster.DoesNotExist:
            pass
        
        # Check expiry status
        expiry_status, is_expired = check_expiry_status(expiry_date)
        
        # Calculate total stock
        total_stock = current_stock + current_free_qty
        
        # Update or create batch cache
        batch_cache, created = BatchInventoryCache.objects.update_or_create(
            product_id=product_id,
            batch_no=batch_no,
            expiry_date=expiry_date,
            defaults={
                'current_stock': current_stock,
                'current_free_qty': current_free_qty,
                'total_stock': total_stock,
                'mrp': mrp,
                'purchase_rate': purchase_rate,
                'rate_a': rate_a,
                'rate_b': rate_b,
                'rate_c': rate_c,
                'is_expired': is_expired,
                'expiry_status': expiry_status,
            }
        )
        
        return batch_cache
    except Exception as e:
        print(f"[ERROR] update_batch_cache: {e}")
        return None


def update_product_cache(product_id):
    """Update cache for a product (summary level) - OPTIMIZED"""
    try:
        # OLD: Multiple queries and Python loops (SLOW)
        # NEW: Single query with aggregation (FAST)
        
        # Get active batches only (total_stock > 0)
        active_batches = BatchInventoryCache.objects.filter(
            product_id=product_id,
            total_stock__gt=0
        ).only('total_stock', 'current_stock', 'mrp', 'purchase_rate', 'is_expired')
        
        # Single aggregation query for all stats
        stats = active_batches.aggregate(
            total_stock=Sum('total_stock'),
            total_batches=Count('id'),
            avg_mrp=Avg('mrp'),
            avg_purchase_rate=Avg('purchase_rate')
        )
        
        total_stock = stats['total_stock'] or 0
        total_batches = stats['total_batches'] or 0
        avg_mrp = stats['avg_mrp'] or 0
        avg_purchase_rate = stats['avg_purchase_rate'] or 0
        
        # Calculate stock value (optimized with list comprehension)
        total_stock_value = sum(b.total_stock * b.mrp for b in active_batches)
        
        # ✅ AUTO-DELETE: If all values are zero, delete the product cache row
        if (total_stock == 0 and total_batches == 0 and 
            avg_mrp == 0 and avg_purchase_rate == 0 and total_stock_value == 0):
            deleted_count = ProductInventoryCache.objects.filter(product_id=product_id).delete()[0]
            if deleted_count > 0:
                print(f"🗑️ Auto-deleted ProductInventoryCache for product {product_id} (all values zero)")
            return None
        
        # Determine stock status (OPTIMIZED logic)
        if total_stock <= 0:
            stock_status = 'out_of_stock'
        elif total_stock <= 10:
            stock_status = 'low_stock'
        else:
            stock_status = 'in_stock'
        
        # Check for expired batches (single query)
        has_expired_batches = BatchInventoryCache.objects.filter(
            product_id=product_id,
            is_expired=True
        ).exists()
        
        # Update or create product cache (ATOMIC operation)
        product_cache, created = ProductInventoryCache.objects.update_or_create(
            product_id=product_id,
            defaults={
                'total_stock': total_stock,
                'total_batches': total_batches,
                'avg_mrp': avg_mrp,
                'avg_purchase_rate': avg_purchase_rate,
                'total_stock_value': total_stock_value,
                'stock_status': stock_status,
                'has_expired_batches': has_expired_batches,
            }
        )
        
        return product_cache
    except Exception as e:
        print(f"[ERROR] update_product_cache for product {product_id}: {e}")
        return None


def update_all_batches_for_product(product_id):
    """Update all batch caches for a product"""
    try:
        # Get all unique batch combinations from all sources
        all_batches = set()
        
        for model, batch_field, expiry_field in [
            (PurchaseMaster, 'product_batch_no', 'product_expiry'),
            (SalesMaster, 'product_batch_no', 'product_expiry'),
            (ReturnPurchaseMaster, 'returnproduct_batch_no', None),
            (ReturnSalesMaster, 'return_product_batch_no', 'return_product_expiry'),
            (SupplierChallanMaster, 'product_batch_no', 'product_expiry'),
            (CustomerChallanMaster, 'product_batch_no', 'product_expiry'),
        ]:
            filter_key = 'productid' if model in [PurchaseMaster, SalesMaster] else 'returnproductid' if model == ReturnPurchaseMaster else 'return_productid' if model == ReturnSalesMaster else 'product_id'
            
            if expiry_field:
                batches = model.objects.filter(**{filter_key: product_id}).values(batch_field, expiry_field).distinct()
                for b in batches:
                    all_batches.add((b[batch_field], b[expiry_field]))
            else:
                batches = model.objects.filter(**{filter_key: product_id}).values(batch_field).distinct()
                for b in batches:
                    all_batches.add((b[batch_field], None))
        
        # Update each batch
        for batch_no, expiry_date in all_batches:
            if batch_no:
                update_batch_cache(product_id, batch_no, expiry_date)
        
        # Update product summary
        update_product_cache(product_id)
        
        return True
    except Exception as e:
        print(f"[ERROR] update_all_batches_for_product: {e}")
        return False


def update_cache_after_sales_return(return_sales_master):
    """Update cache after sales return - Stock INCREASES"""
    try:
        product_id = return_sales_master.return_productid_id
        batch_no = return_sales_master.return_product_batch_no
        expiry_date = return_sales_master.return_product_expiry
        
        # Update batch cache
        update_batch_cache(product_id, batch_no, expiry_date)
        
        # Update product summary
        update_product_cache(product_id)
        
        print(f"✅ Cache updated after sales return: Product {product_id}, Batch {batch_no}")
        return True
    except Exception as e:
        print(f"❌ Error updating cache after sales return: {e}")
        return False


def rebuild_all_cache():
    """Rebuild entire cache for all products - OPTIMIZED"""
    print("[INFO] Starting cache rebuild...")
    
    # OLD: Load all products at once (MEMORY INTENSIVE)
    # NEW: Use iterator() to process in chunks (MEMORY EFFICIENT)
    products = ProductMaster.objects.only('productid').iterator(chunk_size=100)
    total = ProductMaster.objects.count()
    
    success_count = 0
    error_count = 0
    
    for idx, product in enumerate(products, 1):
        try:
            update_all_batches_for_product(product.productid)
            success_count += 1
            
            # Progress update every 50 products (less console spam)
            if idx % 50 == 0:
                print(f"[INFO] Progress: {idx}/{total} products ({(idx/total)*100:.1f}%) - Success: {success_count}, Errors: {error_count}")
        except Exception as e:
            error_count += 1
            print(f"[ERROR] Failed for product {product.productid}: {e}")
    
    print(f"[OK] Cache rebuild completed!")
    print(f"    Total: {total} | Success: {success_count} | Errors: {error_count}")
    return True
