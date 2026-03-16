"""
Test script to verify Free Qty functionality in Purchase Invoice
This script will:
1. Create a test purchase invoice with free quantity
2. Verify if free_qty is saved in database
3. Check if it displays correctly in invoice detail
"""

import os
import django
import sys

# Setup Django environment
sys.path.append(r'c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebsiteHostingService.settings')
django.setup()

from core.models import (
    InvoiceMaster, PurchaseMaster, SupplierMaster, 
    ProductMaster, InvoiceSeries
)
from datetime import datetime, date
from django.db import transaction

def test_free_qty_functionality():
    print("=" * 80)
    print("TESTING FREE QTY FUNCTIONALITY IN PURCHASE INVOICE")
    print("=" * 80)
    
    try:
        # Step 1: Get or create a test supplier
        print("\n[STEP 1] Getting/Creating Test Supplier...")
        supplier, created = SupplierMaster.objects.get_or_create(
            supplier_name="TEST_SUPPLIER_FREE_QTY",
            defaults={
                'supplier_mobile': '9999999999',
                'supplier_address': 'Test Address',
                'supplier_type': 'Test'
            }
        )
        print(f"✓ Supplier: {supplier.supplier_name} (ID: {supplier.supplierid})")
        if created:
            print("  → New supplier created")
        else:
            print("  → Existing supplier found")
        
        # Step 2: Get or create a test product
        print("\n[STEP 2] Getting/Creating Test Product...")
        product, created = ProductMaster.objects.get_or_create(
            product_name="TEST_PRODUCT_FREE_QTY",
            defaults={
                'product_company': 'Test Company',
                'product_packing': '10x10',
                'product_MRP': 100.00,
                'product_HSN': '12345678'
            }
        )
        print(f"✓ Product: {product.product_name} (ID: {product.productid})")
        if created:
            print("  → New product created")
        else:
            print("  → Existing product found")
        
        # Step 3: Create test invoice
        print("\n[STEP 3] Creating Test Invoice...")
        with transaction.atomic():
            # Generate unique invoice number
            invoice_no = f"TEST_FREE_QTY_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            invoice = InvoiceMaster.objects.create(
                invoice_no=invoice_no,
                invoice_date=date.today(),
                supplierid=supplier,
                transport_charges=50.00,
                invoice_total=0.00,  # Will be updated after adding products
                invoice_paid=0.00
            )
            print(f"✓ Invoice Created: {invoice.invoice_no} (ID: {invoice.invoiceid})")
            
            # Step 4: Create purchase entry with FREE QTY
            print("\n[STEP 4] Creating Purchase Entry with Free Qty...")
            
            # Test data
            paid_qty = 100.0
            free_qty = 25.0  # FREE QUANTITY TO TEST
            purchase_rate = 80.00
            mrp = 100.00
            discount = 50.00
            cgst = 6.0
            sgst = 6.0
            
            # Calculate amounts (only for paid quantity)
            base_amount = purchase_rate * paid_qty
            after_discount = base_amount - discount
            cgst_amount = (after_discount * cgst) / 100
            sgst_amount = (after_discount * sgst) / 100
            total_amount = after_discount + cgst_amount + sgst_amount
            
            purchase = PurchaseMaster.objects.create(
                product_supplierid=supplier,
                product_invoiceid=invoice,
                product_invoice_no=invoice.invoice_no,
                productid=product,
                product_name=product.product_name,
                product_company=product.product_company,
                product_packing=product.product_packing,
                product_batch_no='BATCH_TEST_001',
                product_expiry='12-2025',
                product_MRP=mrp,
                product_purchase_rate=purchase_rate,
                product_quantity=paid_qty,
                product_free_qty=free_qty,  # FREE QTY FIELD
                product_scheme=0.0,
                product_discount_got=discount,
                CGST=cgst,
                SGST=sgst,
                purchase_calculation_mode='flat',
                actual_rate_per_qty=purchase_rate - (discount / paid_qty),
                product_actual_rate=purchase_rate - (discount / paid_qty),
                total_amount=total_amount,
                product_transportation_charges=0.0,
                rate_a=90.00,
                rate_b=85.00,
                rate_c=82.00
            )
            
            print(f"✓ Purchase Entry Created (ID: {purchase.purchaseid})")
            print(f"  → Paid Quantity: {purchase.product_quantity}")
            print(f"  → Free Quantity: {purchase.product_free_qty}")
            print(f"  → Total Quantity: {purchase.product_quantity + purchase.product_free_qty}")
            print(f"  → Purchase Rate: ₹{purchase.product_purchase_rate}")
            print(f"  → Total Amount: ₹{purchase.total_amount:.2f}")
            
            # Update invoice total
            invoice.invoice_total = total_amount + invoice.transport_charges
            invoice.save()
            print(f"  → Invoice Total Updated: ₹{invoice.invoice_total:.2f}")
        
        # Step 5: Verify data in database
        print("\n[STEP 5] Verifying Data in Database...")
        
        # Fetch the purchase entry again from database
        saved_purchase = PurchaseMaster.objects.get(purchaseid=purchase.purchaseid)
        
        print(f"✓ Database Verification:")
        print(f"  → Purchase ID: {saved_purchase.purchaseid}")
        print(f"  → Product: {saved_purchase.product_name}")
        print(f"  → Batch: {saved_purchase.product_batch_no}")
        print(f"  → Paid Qty: {saved_purchase.product_quantity}")
        print(f"  → Free Qty: {saved_purchase.product_free_qty}")
        print(f"  → MRP: ₹{saved_purchase.product_MRP}")
        print(f"  → Purchase Rate: ₹{saved_purchase.product_purchase_rate}")
        print(f"  → Total Amount: ₹{saved_purchase.total_amount:.2f}")
        
        # Step 6: Check if free_qty is properly saved
        print("\n[STEP 6] Checking Free Qty Value...")
        if saved_purchase.product_free_qty == free_qty:
            print(f"✅ SUCCESS! Free Qty is correctly saved: {saved_purchase.product_free_qty}")
        else:
            print(f"❌ FAILED! Free Qty mismatch:")
            print(f"   Expected: {free_qty}")
            print(f"   Found: {saved_purchase.product_free_qty}")
        
        # Step 7: Simulate invoice detail view data
        print("\n[STEP 7] Simulating Invoice Detail View...")
        invoice_data = InvoiceMaster.objects.get(invoiceid=invoice.invoiceid)
        purchases_data = PurchaseMaster.objects.filter(product_invoiceid=invoice.invoiceid)
        
        print(f"✓ Invoice Detail Data:")
        print(f"  → Invoice No: {invoice_data.invoice_no}")
        print(f"  → Invoice Date: {invoice_data.invoice_date}")
        print(f"  → Supplier: {invoice_data.supplierid.supplier_name}")
        print(f"  → Transport Charges: ₹{invoice_data.transport_charges:.2f}")
        print(f"  → Invoice Total: ₹{invoice_data.invoice_total:.2f}")
        print(f"\n  Products in Invoice:")
        
        for idx, p in enumerate(purchases_data, 1):
            print(f"\n  Product #{idx}:")
            print(f"    - Name: {p.product_name}")
            print(f"    - Batch: {p.product_batch_no}")
            print(f"    - Expiry: {p.product_expiry}")
            print(f"    - MRP: ₹{p.product_MRP}")
            print(f"    - Rate: ₹{p.product_purchase_rate}")
            print(f"    - Paid Qty: {p.product_quantity}")
            print(f"    - Free Qty: {p.product_free_qty} ← CHECK THIS VALUE")
            print(f"    - Total Qty: {p.product_quantity + p.product_free_qty}")
            print(f"    - Discount: ₹{p.product_discount_got}")
            print(f"    - CGST: {p.CGST}%")
            print(f"    - SGST: {p.SGST}%")
            print(f"    - Total: ₹{p.total_amount:.2f}")
        
        # Step 8: Final Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✓ Test Invoice Created: {invoice.invoice_no}")
        print(f"✓ Invoice ID: {invoice.invoiceid}")
        print(f"✓ Purchase Entry ID: {purchase.purchaseid}")
        print(f"✓ Paid Quantity: {saved_purchase.product_quantity}")
        print(f"✓ Free Quantity: {saved_purchase.product_free_qty}")
        
        if saved_purchase.product_free_qty > 0:
            print(f"\n✅ FREE QTY FEATURE IS WORKING CORRECTLY!")
            print(f"   Free Qty value ({saved_purchase.product_free_qty}) is saved in database.")
        else:
            print(f"\n❌ FREE QTY FEATURE HAS ISSUES!")
            print(f"   Free Qty value is 0 in database (Expected: {free_qty})")
        
        print(f"\n📋 To view this invoice in browser:")
        print(f"   URL: http://localhost:8000/invoices/{invoice.invoiceid}/")
        print(f"\n🗑️  To delete test data, run:")
        print(f"   python manage.py shell -c \"from core.models import InvoiceMaster, PurchaseMaster; InvoiceMaster.objects.filter(invoice_no='{invoice.invoice_no}').delete()\"")
        
        print("\n" + "=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        print("\nFull Traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_free_qty_functionality()
