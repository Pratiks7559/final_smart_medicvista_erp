"""
Comprehensive Inventory Flow Test
Tests: Purchase -> Customer Challan -> Sales Invoice -> Delete Sales
Shows transaction history and stock at each step
"""

import os
import sys
import django

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Setup Django
sys.path.append(r'c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService\pharmamgmt')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from django.utils import timezone
from decimal import Decimal
from core.models import (
    ProductMaster, SupplierMaster, CustomerMaster, InvoiceMaster,
    PurchaseMaster, CustomerChallan, CustomerChallanMaster,
    SalesInvoiceMaster, SalesMaster, InventoryTransaction
)


def print_separator(title):
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def print_transactions(product, batch_no):
    """Print all transactions for a product-batch"""
    transactions = InventoryTransaction.objects.filter(
        product=product,
        batch_no=batch_no
    ).order_by('transaction_date', 'transaction_id')
    
    if not transactions.exists():
        print("❌ No transactions found!")
        return
    
    print(f"\n📋 Transaction History for {product.product_name} - Batch: {batch_no}")
    print("-" * 120)
    print(f"{'Date':<20} {'Type':<20} {'Ref Type':<10} {'Ref ID':<10} {'Qty':<10} {'Free Qty':<10} {'Balance':<10} {'Remarks':<30}")
    print("-" * 120)
    
    running_balance = Decimal('0')
    for txn in transactions:
        running_balance += txn.quantity + txn.free_quantity
        print(f"{txn.transaction_date.strftime('%d-%m-%Y %H:%M'):<20} "
              f"{txn.transaction_type:<20} "
              f"{txn.reference_type:<10} "
              f"{txn.reference_id:<10} "
              f"{txn.quantity:>9.2f} "
              f"{txn.free_quantity:>9.2f} "
              f"{running_balance:>9.2f} "
              f"{txn.remarks[:30]:<30}")
    
    print("-" * 120)
    print(f"✅ Total Transactions: {transactions.count()}")
    print(f"📊 Final Balance: {running_balance}")


def check_stock(product, batch_no):
    """Check current stock for product-batch"""
    stock_data = InventoryTransaction.get_batch_stock(product.productid, batch_no)
    print(f"\n📦 Current Stock for {product.product_name} - Batch: {batch_no}")
    print(f"   Regular Stock: {stock_data['stock']}")
    print(f"   Free Stock: {stock_data['free_stock']}")
    print(f"   Total Stock: {stock_data['total_stock']}")
    return stock_data


def cleanup_test_data():
    """Clean up any existing test data"""
    print_separator("CLEANUP: Removing existing test data")
    
    # Delete in reverse order of dependencies
    SalesMaster.objects.filter(product_name__icontains='TEST_PRODUCT').delete()
    SalesInvoiceMaster.objects.filter(sales_invoice_no__startswith='TEST_').delete()
    CustomerChallanMaster.objects.filter(product_name__icontains='TEST_PRODUCT').delete()
    CustomerChallan.objects.filter(customer_challan_no__startswith='TEST_').delete()
    PurchaseMaster.objects.filter(product_name__icontains='TEST_PRODUCT').delete()
    InvoiceMaster.objects.filter(invoice_no__startswith='TEST_').delete()
    InventoryTransaction.objects.filter(remarks__icontains='TEST').delete()
    ProductMaster.objects.filter(product_name__icontains='TEST_PRODUCT').delete()
    
    print("✅ Cleanup completed")


def run_test():
    """Run comprehensive inventory flow test"""
    
    print_separator("COMPREHENSIVE INVENTORY FLOW TEST")
    print("Testing: Purchase -> Customer Challan -> Sales Invoice -> Delete Sales")
    print("Tracking: Transaction History & Stock at each step")
    
    # Cleanup first
    cleanup_test_data()
    
    # Get or create test entities
    print_separator("STEP 0: Setup Test Data")
    
    # Create test product
    product = ProductMaster.objects.create(
        product_name='TEST_PRODUCT_PARACETAMOL',
        product_company='TEST_PHARMA',
        product_packing='10x10',
        product_salt='Paracetamol',
        product_category='Tablet',
        product_hsn='3004',
        product_hsn_percent='12'
    )
    print(f"✅ Created Product: {product.product_name} (ID: {product.productid})")
    
    # Get supplier
    supplier = SupplierMaster.objects.first()
    if not supplier:
        supplier = SupplierMaster.objects.create(
            supplier_name='TEST_SUPPLIER',
            supplier_mobile='9999999999'
        )
    print(f"✅ Using Supplier: {supplier.supplier_name}")
    
    # Get customer
    customer = CustomerMaster.objects.first()
    if not customer:
        customer = CustomerMaster.objects.create(
            customer_name='TEST_CUSTOMER',
            customer_mobile='8888888888'
        )
    print(f"✅ Using Customer: {customer.customer_name}")
    
    batch_no = 'TEST_BATCH_001'
    
    # ============================================
    # STEP 1: CREATE PURCHASE
    # ============================================
    print_separator("STEP 1: Create Purchase Entry")
    
    invoice = InvoiceMaster.objects.create(
        invoice_no='TEST_INV_001',
        invoice_date=timezone.now().date(),
        supplierid=supplier,
        transport_charges=0,
        invoice_total=100,
        invoice_paid=0
    )
    
    purchase = PurchaseMaster.objects.create(
        product_supplierid=supplier,
        product_invoiceid=invoice,
        product_invoice_no='TEST_INV_001',
        productid=product,
        product_name=product.product_name,
        product_company=product.product_company,
        product_packing=product.product_packing,
        product_batch_no=batch_no,
        product_expiry='12-2025',
        product_MRP=10.0,
        product_purchase_rate=8.0,
        product_quantity=10.0,
        product_free_qty=2.0,
        product_scheme=0,
        product_discount_got=0,
        product_transportation_charges=0,
        actual_rate_per_qty=8.0,
        product_actual_rate=8.0,
        total_amount=80.0,
        purchase_entry_date=timezone.now(),
        CGST=2.5,
        SGST=2.5
    )
    
    print(f"✅ Purchase Created:")
    print(f"   Product: {purchase.product_name}")
    print(f"   Batch: {purchase.product_batch_no}")
    print(f"   Quantity: {purchase.product_quantity}")
    print(f"   Free Qty: {purchase.product_free_qty}")
    print(f"   Rate: ₹{purchase.product_purchase_rate}")
    
    print_transactions(product, batch_no)
    stock1 = check_stock(product, batch_no)
    
    # ============================================
    # STEP 2: CREATE CUSTOMER CHALLAN
    # ============================================
    print_separator("STEP 2: Create Customer Challan")
    
    challan_header = CustomerChallan.objects.create(
        customer_challan_no='TEST_CHALLAN_001',
        customer_challan_date=timezone.now().date(),
        customer_name=customer,
        customer_transport_charges=0,
        challan_total=20.0,
        challan_invoice_paid=0,
        is_invoiced=False
    )
    
    challan = CustomerChallanMaster.objects.create(
        customer_challan_id=challan_header,
        customer_challan_no='TEST_CHALLAN_001',
        customer_name=customer,
        product_id=product,
        product_name=product.product_name,
        product_company=product.product_company,
        product_packing=product.product_packing,
        product_batch_no=batch_no,
        product_expiry='12-2025',
        product_mrp=10.0,
        sale_rate=9.0,
        sale_quantity=5.0,
        sale_free_qty=1.0,
        sale_discount=0,
        sale_cgst=2.5,
        sale_sgst=2.5,
        sale_total_amount=45.0,
        sales_entry_date=timezone.now()
    )
    
    print(f"✅ Customer Challan Created:")
    print(f"   Challan No: {challan.customer_challan_no}")
    print(f"   Product: {challan.product_name}")
    print(f"   Batch: {challan.product_batch_no}")
    print(f"   Quantity: {challan.sale_quantity}")
    print(f"   Free Qty: {challan.sale_free_qty}")
    print(f"   Rate: ₹{challan.sale_rate}")
    
    print_transactions(product, batch_no)
    stock2 = check_stock(product, batch_no)
    
    # ============================================
    # STEP 3: PULL CHALLAN TO SALES INVOICE
    # ============================================
    print_separator("STEP 3: Pull Challan to Sales Invoice")
    
    sales_invoice = SalesInvoiceMaster.objects.create(
        sales_invoice_no='TEST_SALES_001',
        sales_invoice_date=timezone.now().date(),
        customerid=customer,
        sales_transport_charges=0,
        sales_invoice_paid=0
    )
    
    sale = SalesMaster.objects.create(
        sales_invoice_no=sales_invoice,
        customerid=customer,
        productid=product,
        product_name=product.product_name,
        product_company=product.product_company,
        product_packing=product.product_packing,
        product_batch_no=batch_no,
        product_expiry='12-2025',
        product_MRP=10.0,
        sale_rate=9.0,
        sale_quantity=5.0,
        sale_free_qty=1.0,
        sale_scheme=0,
        sale_discount=0,
        sale_cgst=2.5,
        sale_sgst=2.5,
        sale_total_amount=45.0,
        sale_entry_date=timezone.now(),
        source_challan_no='TEST_CHALLAN_001',
        source_challan_date=timezone.now().date()
    )
    
    print(f"✅ Sales Invoice Created from Challan:")
    print(f"   Invoice No: {sales_invoice.sales_invoice_no}")
    print(f"   Source Challan: {sale.source_challan_no}")
    print(f"   Product: {sale.product_name}")
    print(f"   Batch: {sale.product_batch_no}")
    print(f"   Quantity: {sale.sale_quantity}")
    print(f"   Free Qty: {sale.sale_free_qty}")
    print(f"   Rate: ₹{sale.sale_rate}")
    
    print_transactions(product, batch_no)
    stock3 = check_stock(product, batch_no)
    
    # ============================================
    # STEP 4: DELETE SALES INVOICE
    # ============================================
    print_separator("STEP 4: Delete Sales Invoice (Should Revert to Challan)")
    
    sale_id = sale.id
    print(f"🗑️  Deleting Sales Invoice ID: {sale_id}")
    sale.delete()
    print(f"✅ Sales Invoice Deleted")
    
    print_transactions(product, batch_no)
    stock4 = check_stock(product, batch_no)
    
    # ============================================
    # SUMMARY & VALIDATION
    # ============================================
    print_separator("TEST SUMMARY & VALIDATION")
    
    print("\n📊 Stock Changes:")
    print(f"   After Purchase:        Total = {stock1['total_stock']} (Regular: {stock1['stock']}, Free: {stock1['free_stock']})")
    print(f"   After Challan:         Total = {stock2['total_stock']} (Regular: {stock2['stock']}, Free: {stock2['free_stock']})")
    print(f"   After Sales Invoice:   Total = {stock3['total_stock']} (Regular: {stock3['stock']}, Free: {stock3['free_stock']})")
    print(f"   After Delete Invoice:  Total = {stock4['total_stock']} (Regular: {stock4['stock']}, Free: {stock4['free_stock']})")
    
    print("\n✅ Expected Results:")
    print("   1. After Purchase: Stock should be +12 (10 regular + 2 free)")
    print("   2. After Challan: Stock should be +6 (12 - 5 - 1 = 6)")
    print("   3. After Sales Invoice: Stock should remain +6 (challan converted to sale)")
    print("   4. After Delete: Stock should be +6 (sale reverted to challan)")
    
    print("\n🔍 Validation:")
    
    # Check transaction count
    final_txn_count = InventoryTransaction.objects.filter(
        product=product,
        batch_no=batch_no
    ).count()
    
    print(f"\n   Total Transactions: {final_txn_count}")
    
    # Check for duplicates
    from django.db.models import Count
    duplicates = InventoryTransaction.objects.filter(
        product=product,
        batch_no=batch_no
    ).values('transaction_type', 'reference_type', 'reference_id').annotate(
        count=Count('transaction_id')
    ).filter(count__gt=1)
    
    if duplicates.exists():
        print(f"   ❌ DUPLICATES FOUND: {duplicates.count()} groups")
        for dup in duplicates:
            print(f"      - {dup['transaction_type']} / {dup['reference_type']} / {dup['reference_id']}: {dup['count']} entries")
    else:
        print(f"   ✅ No duplicates found")
    
    # Check stock consistency
    if stock2['total_stock'] == stock3['total_stock'] == stock4['total_stock']:
        print(f"   ✅ Stock consistent after challan->sale->delete: {stock4['total_stock']}")
    else:
        print(f"   ❌ Stock inconsistent!")
        print(f"      Challan: {stock2['total_stock']}, Sale: {stock3['total_stock']}, After Delete: {stock4['total_stock']}")
    
    # Check expected stock
    expected_stock = Decimal('12') - Decimal('6')  # Purchase (10+2) - Challan (5+1)
    if stock4['total_stock'] == expected_stock:
        print(f"   ✅ Final stock matches expected: {expected_stock}")
    else:
        print(f"   ❌ Final stock mismatch! Expected: {expected_stock}, Got: {stock4['total_stock']}")
    
    # Check for CUSTOMER_CHALLAN transaction after delete
    challan_txn = InventoryTransaction.objects.filter(
        product=product,
        batch_no=batch_no,
        transaction_type='CUSTOMER_CHALLAN',
        reference_number='TEST_CHALLAN_001'
    )
    
    if challan_txn.count() == 1:
        txn = challan_txn.first()
        print(f"   ✅ Single CUSTOMER_CHALLAN transaction exists")
        print(f"      Quantity: {txn.quantity}, Free Qty: {txn.free_quantity}")
        
        if txn.free_quantity == Decimal('-1'):
            print(f"      ✅ Free quantity is correct: -1")
        else:
            print(f"      ❌ Free quantity incorrect! Expected: -1, Got: {txn.free_quantity}")
    elif challan_txn.count() == 0:
        print(f"   ❌ No CUSTOMER_CHALLAN transaction found after delete!")
    else:
        print(f"   ❌ Multiple CUSTOMER_CHALLAN transactions found: {challan_txn.count()}")
    
    print_separator("TEST COMPLETED")
    
    # Ask if cleanup needed
    print("\n⚠️  Test data created. Do you want to clean it up? (y/n): ", end='')
    # For automated testing, auto-cleanup
    # cleanup_test_data()


if __name__ == '__main__':
    try:
        run_test()
    except Exception as e:
        print(f"\n❌ TEST FAILED WITH ERROR:")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
