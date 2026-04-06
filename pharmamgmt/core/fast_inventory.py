from django.db.models import Sum, Q
from collections import defaultdict
from .models import PurchaseMaster, SalesMaster, ReturnPurchaseMaster, ReturnSalesMaster, SupplierChallanMaster, ProductMaster, CustomerChallanMaster, StockIssueDetail, InvoiceMaster, Challan1

class FastInventory:
    @staticmethod
    def get_fy_product_ids(fy_start, fy_end):
        """Get product IDs whose purchase invoice date OR challan date falls in given FY"""
        invoice_ids = list(
            InvoiceMaster.objects.filter(
                invoice_date__gte=fy_start,
                invoice_date__lte=fy_end
            ).values_list('invoiceid', flat=True)
        )
        purchase_pids = set(
            PurchaseMaster.objects.filter(
                product_invoiceid__in=invoice_ids
            ).values_list('productid_id', flat=True)
        )
        # Also include products that came via supplier challan in this FY
        challan_pids = set(
            SupplierChallanMaster.objects.filter(
                product_challan_id__challan_date__gte=fy_start,
                product_challan_id__challan_date__lte=fy_end
            ).values_list('product_id_id', flat=True)
        )
        return list(purchase_pids | challan_pids)

    @staticmethod
    def get_batch_inventory_data(search_query='', fy_product_ids=None):
        """Optimized batch inventory - fetch all data in bulk"""
        products_query = ProductMaster.objects.all().order_by('product_name')
        if search_query:
            products_query = products_query.filter(
                Q(product_name__icontains=search_query) | Q(product_company__icontains=search_query)
            )
        if fy_product_ids is not None:
            products_query = products_query.filter(productid__in=fy_product_ids)
        
        product_ids = list(products_query.values_list('productid', flat=True))
        products_dict = {p.productid: p for p in products_query}
        
        # Bulk fetch all transactions with expiry
        purchases = defaultdict(lambda: {'qty': 0, 'free_qty': 0, 'mrp': 0, 'expiry': None})
        for p in PurchaseMaster.objects.filter(productid__in=product_ids).values('productid', 'product_batch_no', 'product_quantity', 'product_free_qty', 'product_MRP', 'product_expiry'):
            key = (p['productid'], p['product_batch_no'])
            purchases[key]['qty'] += p['product_quantity']
            purchases[key]['free_qty'] += p['product_free_qty'] or 0
            if not purchases[key]['mrp']:
                purchases[key]['mrp'] = p['product_MRP'] or 0
            if not purchases[key]['expiry']:
                purchases[key]['expiry'] = p['product_expiry']
        
        for c in SupplierChallanMaster.objects.filter(product_id__in=product_ids).values('product_id', 'product_batch_no', 'product_quantity', 'product_free_qty', 'product_mrp', 'product_expiry'):
            key = (c['product_id'], c['product_batch_no'])
            purchases[key]['qty'] += c['product_quantity']
            purchases[key]['free_qty'] += c['product_free_qty'] or 0
            if not purchases[key]['mrp']:
                purchases[key]['mrp'] = c['product_mrp'] or 0
            if not purchases[key]['expiry']:
                purchases[key]['expiry'] = c['product_expiry']
        
        sales = defaultdict(int)
        sales_free = defaultdict(int)
        for s in SalesMaster.objects.filter(productid__in=product_ids).values('productid', 'product_batch_no').annotate(total=Sum('sale_quantity'), total_free=Sum('sale_free_qty')):
            sales[(s['productid'], s['product_batch_no'])] = s['total']
            sales_free[(s['productid'], s['product_batch_no'])] = s['total_free'] or 0
        
        # Add customer challan sales (both regular and free qty)
        for cc in CustomerChallanMaster.objects.filter(product_id__in=product_ids).values('product_id', 'product_batch_no').annotate(total=Sum('sale_quantity'), total_free=Sum('sale_free_qty')):
            key = (cc['product_id'], cc['product_batch_no'])
            sales[key] += cc['total']
            sales_free[key] += cc['total_free'] or 0
        
        pr = defaultdict(int)
        pr_free = defaultdict(int)
        for r in ReturnPurchaseMaster.objects.filter(returnproductid__in=product_ids).values('returnproductid', 'returnproduct_batch_no').annotate(total=Sum('returnproduct_quantity'), total_free=Sum('returnproduct_free_qty')):
            pr[(r['returnproductid'], r['returnproduct_batch_no'])] = r['total']
            pr_free[(r['returnproductid'], r['returnproduct_batch_no'])] = r['total_free'] or 0
        
        sr = defaultdict(int)
        sr_free = defaultdict(int)
        for r in ReturnSalesMaster.objects.filter(return_productid__in=product_ids).values('return_productid', 'return_product_batch_no').annotate(total=Sum('return_sale_quantity'), total_free=Sum('return_sale_free_qty')):
            sr[(r['return_productid'], r['return_product_batch_no'])] = r['total']
            sr_free[(r['return_productid'], r['return_product_batch_no'])] = r['total_free'] or 0
        
        # CRITICAL FIX: Add stock issues to calculation
        stock_issues = defaultdict(int)
        for si in StockIssueDetail.objects.filter(product__in=product_ids).values('product', 'batch_no').annotate(total=Sum('quantity_issued')):
            stock_issues[(si['product'], si['batch_no'])] = si['total']
        
        # Calculate inventory - FIXED to include stock issues
        inventory = []
        for key, data in purchases.items():
            pid, batch = key
            stock = data['qty'] - sales.get(key, 0) - pr.get(key, 0) + sr.get(key, 0) - stock_issues.get(key, 0)
            free_qty = data['free_qty'] - sales_free.get(key, 0) - pr_free.get(key, 0) + sr_free.get(key, 0)
            
            # Apply max(0, ...) to prevent negative values
            stock = max(0, stock)
            free_qty = max(0, free_qty)
            
            # Total stock includes both regular stock and free qty
            total_stock = stock + free_qty
            
            if total_stock > 0 and pid in products_dict:
                p = products_dict[pid]
                inventory.append({
                    'product_id': pid,
                    'product_name': p.product_name,
                    'product_company': p.product_company,
                    'product_packing': p.product_packing,
                    'batch_no': batch,
                    'expiry': data['expiry'] or '',
                    'mrp': data['mrp'],
                    'stock': stock,
                    'free_qty': free_qty,
                    'total_stock': total_stock,
                    'value': stock * data['mrp']  # Value only for paid stock, not free qty
                })
        
        return inventory
    
    @staticmethod
    def get_dateexpiry_inventory_data(search_query='', start_date=None, end_date=None):
        """Optimized date/expiry inventory - filter by invoice_date OR challan_date"""
        products_query = ProductMaster.objects.all()
        if search_query:
            products_query = products_query.filter(
                Q(product_name__icontains=search_query) | Q(product_company__icontains=search_query)
            )

        # Filter product_ids by invoice_date OR challan_date
        if start_date and end_date:
            invoice_pids = set(
                PurchaseMaster.objects.filter(
                    product_invoiceid__invoice_date__gte=start_date,
                    product_invoiceid__invoice_date__lte=end_date
                ).values_list('productid_id', flat=True)
            )
            challan_pids = set(
                SupplierChallanMaster.objects.filter(
                    product_challan_id__challan_date__gte=start_date,
                    product_challan_id__challan_date__lte=end_date
                ).values_list('product_id_id', flat=True)
            )
            filtered_pids = invoice_pids | challan_pids
            products_query = products_query.filter(productid__in=filtered_pids)

        product_ids = list(products_query.values_list('productid', flat=True))
        products_dict = {p.productid: p for p in products_query}

        # Bulk fetch with expiry
        purchases = defaultdict(lambda: {'qty': 0, 'free_qty': 0, 'rate': 0, 'mrp': 0, 'expiry': None})

        # Purchase filter by invoice_date if date range given
        purchase_qs = PurchaseMaster.objects.filter(productid__in=product_ids)
        if start_date and end_date:
            purchase_qs = purchase_qs.filter(
                product_invoiceid__invoice_date__gte=start_date,
                product_invoiceid__invoice_date__lte=end_date
            )
        for p in purchase_qs.values('productid', 'product_batch_no', 'product_quantity', 'product_free_qty', 'product_actual_rate', 'product_MRP', 'product_expiry'):
            key = (p['productid'], p['product_batch_no'])
            purchases[key]['qty'] += p['product_quantity']
            purchases[key]['free_qty'] += p['product_free_qty'] or 0
            if not purchases[key]['rate']:
                purchases[key]['rate'] = p['product_actual_rate'] or 0
                purchases[key]['mrp'] = p['product_MRP'] or 0
                purchases[key]['expiry'] = p['product_expiry']

        # Challan filter by challan_date if date range given
        challan_qs = SupplierChallanMaster.objects.filter(product_id__in=product_ids)
        if start_date and end_date:
            challan_qs = challan_qs.filter(
                product_challan_id__challan_date__gte=start_date,
                product_challan_id__challan_date__lte=end_date
            )
        for c in challan_qs.values('product_id', 'product_batch_no', 'product_quantity', 'product_free_qty', 'product_purchase_rate', 'product_mrp', 'product_expiry'):
            key = (c['product_id'], c['product_batch_no'])
            purchases[key]['qty'] += c['product_quantity']
            purchases[key]['free_qty'] += c['product_free_qty'] or 0
            if not purchases[key]['rate']:
                purchases[key]['rate'] = c['product_purchase_rate'] or 0
                purchases[key]['mrp'] = c['product_mrp'] or 0
                purchases[key]['expiry'] = c['product_expiry']
        
        sales = defaultdict(int)
        for s in SalesMaster.objects.filter(productid__in=product_ids).values('productid', 'product_batch_no').annotate(total=Sum('sale_quantity')):
            sales[(s['productid'], s['product_batch_no'])] = s['total']
        
        # Add customer challan sales (both regular and free qty)
        sales_free = defaultdict(int)
        for cc in CustomerChallanMaster.objects.filter(product_id__in=product_ids).values('product_id', 'product_batch_no').annotate(total=Sum('sale_quantity'), total_free=Sum('sale_free_qty')):
            key = (cc['product_id'], cc['product_batch_no'])
            sales[key] += cc['total']
            sales_free[key] += cc['total_free'] or 0
        
        pr = defaultdict(int)
        pr_free = defaultdict(int)
        for r in ReturnPurchaseMaster.objects.filter(returnproductid__in=product_ids).values('returnproductid', 'returnproduct_batch_no').annotate(total=Sum('returnproduct_quantity'), total_free=Sum('returnproduct_free_qty')):
            pr[(r['returnproductid'], r['returnproduct_batch_no'])] = r['total']
            pr_free[(r['returnproductid'], r['returnproduct_batch_no'])] = r['total_free'] or 0
        
        sr = defaultdict(int)
        sr_free = defaultdict(int)
        for r in ReturnSalesMaster.objects.filter(return_productid__in=product_ids).values('return_productid', 'return_product_batch_no').annotate(total=Sum('return_sale_quantity'), total_free=Sum('return_sale_free_qty')):
            sr[(r['return_productid'], r['return_product_batch_no'])] = r['total']
            sr_free[(r['return_productid'], r['return_product_batch_no'])] = r['total_free'] or 0
        
        # CRITICAL FIX: Add stock issues to dateexpiry calculation
        stock_issues = defaultdict(int)
        for si in StockIssueDetail.objects.filter(product__in=product_ids).values('product', 'batch_no').annotate(total=Sum('quantity_issued')):
            stock_issues[(si['product'], si['batch_no'])] = si['total']
        
        # Group by expiry
        from datetime import datetime
        import calendar
        grouped = defaultdict(list)
        today = datetime.now().date()
        
        for key, data in purchases.items():
            pid, batch = key
            stock = data['qty'] - sales.get(key, 0) - pr.get(key, 0) + sr.get(key, 0) - stock_issues.get(key, 0)
            free_qty = data.get('free_qty', 0) - sales_free.get(key, 0) - pr_free.get(key, 0) + sr_free.get(key, 0)
            
            # Apply max(0, ...) to prevent negative values
            stock = max(0, stock)
            free_qty = max(0, free_qty)
            total_stock = stock + free_qty
            
            if total_stock > 0 and pid in products_dict:
                p = products_dict[pid]
                expiry = data['expiry']
                
                # Skip products without expiry date
                if not expiry:
                    continue
                
                # Parse expiry
                expiry_key = None
                days = 999999
                try:
                    if isinstance(expiry, str):
                        exp_date = datetime.strptime(expiry, '%m-%Y')
                        # Skip unrealistic dates (more than 10 years in future)
                        if exp_date.year > today.year + 10:
                            continue
                        expiry_key = expiry
                        last_day = calendar.monthrange(exp_date.year, exp_date.month)[1]
                        month_end = datetime(exp_date.year, exp_date.month, last_day).date()
                        days = (month_end - today).days
                    elif hasattr(expiry, 'strftime'):
                        # Skip unrealistic dates (more than 10 years in future)
                        if expiry.year > today.year + 10:
                            continue
                        expiry_key = expiry.strftime('%m-%Y')
                        last_day = calendar.monthrange(expiry.year, expiry.month)[1]
                        month_end = datetime(expiry.year, expiry.month, last_day).date()
                        days = (month_end - today).days
                except:
                    continue
                
                if not expiry_key:
                    continue
                
                grouped[expiry_key].append({
                    'product_name': p.product_name,
                    'product_company': p.product_company,
                    'product_packing': p.product_packing,
                    'batch_no': batch,
                    'quantity': stock,
                    'purchase_rate': data['rate'],
                    'mrp': data['mrp'],
                    'value': stock * data['rate'],
                    'days_to_expiry': days,
                    'expiry_display': expiry_key
                })
        
        # Format output
        result = []
        for exp_key, items in grouped.items():
            total = sum(i['value'] for i in items)
            days = items[0]['days_to_expiry'] if items else 999999
            result.append({
                'expiry_display': exp_key,
                'expiry_date': exp_key,
                'days_to_expiry': days,
                'products': items,
                'total_value': total
            })
        
        result.sort(key=lambda x: x['days_to_expiry'])
        return result, sum(g['total_value'] for g in result)
