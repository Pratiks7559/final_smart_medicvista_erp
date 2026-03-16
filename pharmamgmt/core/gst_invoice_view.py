from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from core.models import InvoiceMaster, PurchaseMaster, SalesInvoiceMaster, SalesMaster, ReturnInvoiceMaster, ReturnPurchaseMaster, ReturnSalesInvoiceMaster, ReturnSalesMaster, Pharmacy_Details
from collections import defaultdict
from decimal import Decimal

@login_required
def print_gst_purchase_invoice(request, invoice_id):
    """Print GST-compliant purchase invoice"""
    print(f"\n\n========== GST INVOICE VIEW CALLED FOR INVOICE ID: {invoice_id} ==========\n")
    
    invoice = get_object_or_404(InvoiceMaster, invoiceid=invoice_id)
    purchases = PurchaseMaster.objects.filter(product_invoiceid=invoice_id).order_by('productid')
    
    print(f"Found {purchases.count()} purchases for this invoice\n")
    
    # Get pharmacy details
    pharmacy = Pharmacy_Details.objects.first()
    
    # Calculate GST summary grouped by GST rate
    gst_summary = defaultdict(lambda: {
        'taxable_amount': Decimal('0'),
        'cgst_amount': Decimal('0'),
        'sgst_amount': Decimal('0'),
        'total_amount': Decimal('0')
    })
    
    items_with_calculations = []
    sr_no = 1
    
    for purchase in purchases:
        # Calculate base amount (after discount)
        base_amount = Decimal(str(purchase.product_purchase_rate)) * Decimal(str(purchase.product_quantity))
        
        if purchase.purchase_calculation_mode == 'flat':
            taxable_amount = base_amount - Decimal(str(purchase.product_discount_got))
        else:
            taxable_amount = base_amount * (Decimal('1') - (Decimal(str(purchase.product_discount_got)) / Decimal('100')))
        
        # Calculate GST amounts
        cgst_rate = Decimal(str(purchase.CGST))
        sgst_rate = Decimal(str(purchase.SGST))
        
        print(f"\nProduct: {purchase.product_name}")
        print(f"CGST Rate: {cgst_rate}, SGST Rate: {sgst_rate}")
        print(f"Total GST Rate: {cgst_rate + sgst_rate}")
        
        cgst_amount = taxable_amount * (cgst_rate / Decimal('100'))
        sgst_amount = taxable_amount * (sgst_rate / Decimal('100'))
        total_amount = taxable_amount + cgst_amount + sgst_amount
        
        # Add to items list
        items_with_calculations.append({
            'sr_no': sr_no,
            'purchase': purchase,
            'taxable_amount': taxable_amount,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'total_amount': total_amount,
            'gst_rate': cgst_rate + sgst_rate
        })
        
        # Add to GST summary - Convert Decimal to float then int for proper rounding
        total_gst_rate = float(cgst_rate + sgst_rate)
        gst_key = str(int(round(total_gst_rate)))
        
        print(f"Total GST Rate (float): {total_gst_rate}")
        print(f"GST Key: '{gst_key}'")
        
        gst_summary[gst_key]['taxable_amount'] += taxable_amount
        gst_summary[gst_key]['cgst_amount'] += cgst_amount
        gst_summary[gst_key]['sgst_amount'] += sgst_amount
        gst_summary[gst_key]['total_amount'] += total_amount
        
        sr_no += 1
    
    # Ensure 5%, 12% and 18% GST rates are always present
    for rate in ['5', '12', '18']:
        if rate not in gst_summary:
            gst_summary[rate] = {
                'taxable_amount': Decimal('0'),
                'cgst_amount': Decimal('0'),
                'sgst_amount': Decimal('0'),
                'total_amount': Decimal('0')
            }
    
    # Calculate totals
    total_taxable = sum(item['taxable_amount'] for item in items_with_calculations)
    total_cgst = sum(item['cgst_amount'] for item in items_with_calculations)
    total_sgst = sum(item['sgst_amount'] for item in items_with_calculations)
    grand_total = total_taxable + total_cgst + total_sgst + Decimal(str(invoice.transport_charges or 0))
    
    # Apply round-off to grand total
    from .roundoff_utils import calculate_roundoff
    roundoff_data = calculate_roundoff(float(grand_total))
    rounded_grand_total = Decimal(str(roundoff_data['rounded_amount']))
    roundoff_amount = Decimal(str(roundoff_data['roundoff_amount']))
    roundoff_type = roundoff_data['roundoff_type']  # 'added' or 'deducted'

    # Convert amount to words (use rounded total)
    amount_in_words = number_to_words(float(rounded_grand_total))
    
    print("\n=== FINAL GST SUMMARY ===")
    print(f"GST Summary Keys: {list(gst_summary.keys())}")
    for key, value in gst_summary.items():
        print(f"Rate {key}%: Taxable={value['taxable_amount']}, CGST={value['cgst_amount']}, SGST={value['sgst_amount']}, Total={value['total_amount']}")
    
    # Extract GST rate data for template (to handle numeric key access issue)
    gst_5 = gst_summary.get('5', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_12 = gst_summary.get('12', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_18 = gst_summary.get('18', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    
    print(f"\ngst_5: {gst_5}")
    print(f"gst_12: {gst_12}")
    print(f"gst_18: {gst_18}")
    print("=== END DEBUG ===\n")
    
    context = {
        'invoice': invoice,
        'items': items_with_calculations,
        'gst_summary': dict(gst_summary),
        'gst_5': gst_5,
        'gst_12': gst_12,
        'gst_18': gst_18,
        'total_taxable': total_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'grand_total': rounded_grand_total,
        'grand_total_before_roundoff': grand_total,
        'roundoff_amount': roundoff_amount,
        'roundoff_type': roundoff_type,
        'amount_in_words': amount_in_words,
        'pharmacy': pharmacy,
    }
    
    return render(request, 'purchases/gst_purchase_invoice.html', context)

@login_required
def print_gst_sales_invoice(request, invoice_id):
    """Print GST-compliant sales invoice"""
    invoice = get_object_or_404(SalesInvoiceMaster, sales_invoice_no=invoice_id)
    sales = SalesMaster.objects.filter(sales_invoice_no=invoice_id).order_by('productid')
    
    pharmacy = Pharmacy_Details.objects.first()
    
    gst_summary = defaultdict(lambda: {
        'taxable_amount': Decimal('0'),
        'cgst_amount': Decimal('0'),
        'sgst_amount': Decimal('0'),
        'total_amount': Decimal('0')
    })
    
    items_with_calculations = []
    sr_no = 1
    
    for sale in sales:
        base_amount = Decimal(str(sale.sale_rate)) * Decimal(str(sale.sale_quantity))
        
        if sale.sale_calculation_mode == 'flat':
            taxable_amount = base_amount - Decimal(str(sale.sale_discount))
        else:
            taxable_amount = base_amount * (Decimal('1') - (Decimal(str(sale.sale_discount)) / Decimal('100')))
        
        cgst_rate = Decimal(str(sale.sale_cgst))
        sgst_rate = Decimal(str(sale.sale_sgst))
        
        cgst_amount = taxable_amount * (cgst_rate / Decimal('100'))
        sgst_amount = taxable_amount * (sgst_rate / Decimal('100'))
        total_amount = taxable_amount + cgst_amount + sgst_amount
        
        items_with_calculations.append({
            'sr_no': sr_no,
            'sale': sale,
            'taxable_amount': taxable_amount,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'total_amount': total_amount,
            'gst_rate': cgst_rate + sgst_rate
        })
        
        total_gst_rate = float(cgst_rate + sgst_rate)
        gst_key = str(int(round(total_gst_rate)))
        
        gst_summary[gst_key]['taxable_amount'] += taxable_amount
        gst_summary[gst_key]['cgst_amount'] += cgst_amount
        gst_summary[gst_key]['sgst_amount'] += sgst_amount
        gst_summary[gst_key]['total_amount'] += total_amount
        
        sr_no += 1
    
    for rate in ['5', '12', '18']:
        if rate not in gst_summary:
            gst_summary[rate] = {
                'taxable_amount': Decimal('0'),
                'cgst_amount': Decimal('0'),
                'sgst_amount': Decimal('0'),
                'total_amount': Decimal('0')
            }
    
    total_taxable = sum(item['taxable_amount'] for item in items_with_calculations)
    total_cgst = sum(item['cgst_amount'] for item in items_with_calculations)
    total_sgst = sum(item['sgst_amount'] for item in items_with_calculations)
    total_discount = sum(Decimal(str(sale.sale_discount)) for sale in sales)
    grand_total = total_taxable + total_cgst + total_sgst
    
    amount_in_words = number_to_words(float(grand_total))
    
    gst_5 = gst_summary.get('5', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_12 = gst_summary.get('12', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_18 = gst_summary.get('18', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    
    context = {
        'invoice': invoice,
        'items': items_with_calculations,
        'gst_summary': dict(gst_summary),
        'gst_5': gst_5,
        'gst_12': gst_12,
        'gst_18': gst_18,
        'total_taxable': total_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'total_discount': total_discount,
        'grand_total': grand_total,
        'amount_in_words': amount_in_words,
        'pharmacy': pharmacy,
    }
    
    return render(request, 'sales/gst_sales_invoice.html', context)

@login_required
def print_gst_purchase_return_invoice(request, return_id):
    """Print GST-compliant purchase return invoice"""
    return_invoice = get_object_or_404(ReturnInvoiceMaster, returninvoiceid=return_id)
    return_items = ReturnPurchaseMaster.objects.filter(returninvoiceid=return_id).order_by('returnproductid')
    
    pharmacy = Pharmacy_Details.objects.first()
    
    gst_summary = defaultdict(lambda: {
        'taxable_amount': Decimal('0'),
        'cgst_amount': Decimal('0'),
        'sgst_amount': Decimal('0'),
        'total_amount': Decimal('0')
    })
    
    items_with_calculations = []
    sr_no = 1
    
    for return_item in return_items:
        base_amount = Decimal(str(return_item.returnproduct_purchase_rate)) * Decimal(str(return_item.returnproduct_quantity))
        
        taxable_amount = base_amount
        
        cgst_rate = Decimal(str(return_item.returnproduct_cgst))
        sgst_rate = Decimal(str(return_item.returnproduct_sgst))
        
        cgst_amount = taxable_amount * (cgst_rate / Decimal('100'))
        sgst_amount = taxable_amount * (sgst_rate / Decimal('100'))
        total_amount = taxable_amount + cgst_amount + sgst_amount
        
        items_with_calculations.append({
            'sr_no': sr_no,
            'return_item': return_item,
            'taxable_amount': taxable_amount,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'total_amount': total_amount,
            'gst_rate': cgst_rate + sgst_rate
        })
        
        total_gst_rate = float(cgst_rate + sgst_rate)
        gst_key = str(int(round(total_gst_rate)))
        
        gst_summary[gst_key]['taxable_amount'] += taxable_amount
        gst_summary[gst_key]['cgst_amount'] += cgst_amount
        gst_summary[gst_key]['sgst_amount'] += sgst_amount
        gst_summary[gst_key]['total_amount'] += total_amount
        
        sr_no += 1
    
    for rate in ['5', '12', '18']:
        if rate not in gst_summary:
            gst_summary[rate] = {
                'taxable_amount': Decimal('0'),
                'cgst_amount': Decimal('0'),
                'sgst_amount': Decimal('0'),
                'total_amount': Decimal('0')
            }
    
    total_taxable = sum(item['taxable_amount'] for item in items_with_calculations)
    total_cgst = sum(item['cgst_amount'] for item in items_with_calculations)
    total_sgst = sum(item['sgst_amount'] for item in items_with_calculations)
    grand_total = total_taxable + total_cgst + total_sgst
    
    amount_in_words = number_to_words(float(grand_total))
    
    gst_5 = gst_summary.get('5', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_12 = gst_summary.get('12', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_18 = gst_summary.get('18', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    
    context = {
        'return_invoice': return_invoice,
        'items': items_with_calculations,
        'gst_summary': dict(gst_summary),
        'gst_5': gst_5,
        'gst_12': gst_12,
        'gst_18': gst_18,
        'total_taxable': total_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'grand_total': grand_total,
        'amount_in_words': amount_in_words,
        'pharmacy': pharmacy,
    }
    
    return render(request, 'returns/gst_purchase_return_invoice.html', context)

def number_to_words(n):
    """Convert number to Indian words"""
    if n == 0:
        return "Zero Rupees Only"
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    
    def convert_below_thousand(num):
        if num == 0:
            return ""
        elif num < 10:
            return ones[num]
        elif num < 20:
            return teens[num - 10]
        elif num < 100:
            return tens[num // 10] + (" " + ones[num % 10] if num % 10 != 0 else "")
        else:
            return ones[num // 100] + " Hundred" + (" " + convert_below_thousand(num % 100) if num % 100 != 0 else "")
    
    crore = int(n // 10000000)
    n %= 10000000
    lakh = int(n // 100000)
    n %= 100000
    thousand = int(n // 1000)
    n %= 1000
    hundred = int(n)
    
    result = []
    if crore > 0:
        result.append(convert_below_thousand(crore) + " Crore")
    if lakh > 0:
        result.append(convert_below_thousand(lakh) + " Lakh")
    if thousand > 0:
        result.append(convert_below_thousand(thousand) + " Thousand")
    if hundred > 0:
        result.append(convert_below_thousand(hundred))
    
    return " ".join(result) + " Rupees Only"


@login_required
def print_gst_sales_return_invoice(request, return_id):
    """Print GST-compliant sales return invoice"""
    return_invoice = get_object_or_404(ReturnSalesInvoiceMaster, return_sales_invoice_no=return_id)
    return_items = ReturnSalesMaster.objects.filter(return_sales_invoice_no=return_id).order_by('return_productid')
    
    pharmacy = Pharmacy_Details.objects.first()
    
    gst_summary = defaultdict(lambda: {
        'taxable_amount': Decimal('0'),
        'cgst_amount': Decimal('0'),
        'sgst_amount': Decimal('0'),
        'total_amount': Decimal('0')
    })
    
    items_with_calculations = []
    sr_no = 1
    
    for return_item in return_items:
        base_amount = Decimal(str(return_item.return_sale_rate)) * Decimal(str(return_item.return_sale_quantity))
        
        taxable_amount = base_amount
        
        cgst_rate = Decimal(str(return_item.return_sale_cgst))
        sgst_rate = Decimal(str(return_item.return_sale_sgst))
        
        cgst_amount = taxable_amount * (cgst_rate / Decimal('100'))
        sgst_amount = taxable_amount * (sgst_rate / Decimal('100'))
        total_amount = taxable_amount + cgst_amount + sgst_amount
        
        items_with_calculations.append({
            'sr_no': sr_no,
            'return_item': return_item,
            'taxable_amount': taxable_amount,
            'cgst_amount': cgst_amount,
            'sgst_amount': sgst_amount,
            'total_amount': total_amount,
            'gst_rate': cgst_rate + sgst_rate
        })
        
        total_gst_rate = float(cgst_rate + sgst_rate)
        gst_key = str(int(round(total_gst_rate)))
        
        gst_summary[gst_key]['taxable_amount'] += taxable_amount
        gst_summary[gst_key]['cgst_amount'] += cgst_amount
        gst_summary[gst_key]['sgst_amount'] += sgst_amount
        gst_summary[gst_key]['total_amount'] += total_amount
        
        sr_no += 1
    
    for rate in ['5', '12', '18']:
        if rate not in gst_summary:
            gst_summary[rate] = {
                'taxable_amount': Decimal('0'),
                'cgst_amount': Decimal('0'),
                'sgst_amount': Decimal('0'),
                'total_amount': Decimal('0')
            }
    
    total_taxable = sum(item['taxable_amount'] for item in items_with_calculations)
    total_cgst = sum(item['cgst_amount'] for item in items_with_calculations)
    total_sgst = sum(item['sgst_amount'] for item in items_with_calculations)
    grand_total = total_taxable + total_cgst + total_sgst
    
    amount_in_words = number_to_words(float(grand_total))
    
    gst_5 = gst_summary.get('5', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_12 = gst_summary.get('12', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    gst_18 = gst_summary.get('18', {'taxable_amount': Decimal('0'), 'cgst_amount': Decimal('0'), 'sgst_amount': Decimal('0'), 'total_amount': Decimal('0')})
    
    context = {
        'return_invoice': return_invoice,
        'items': items_with_calculations,
        'gst_summary': dict(gst_summary),
        'gst_5': gst_5,
        'gst_12': gst_12,
        'gst_18': gst_18,
        'total_taxable': total_taxable,
        'total_cgst': total_cgst,
        'total_sgst': total_sgst,
        'grand_total': grand_total,
        'amount_in_words': amount_in_words,
        'pharmacy': pharmacy,
    }
    
    return render(request, 'returns/gst_sales_return_invoice.html', context)
