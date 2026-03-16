"""
Script to verify Free Qty column in sales invoice detail
"""

# Check template
template_path = r"c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService\templates\sales\sales_invoice_detail.html"

with open(template_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
# Find Free Qty occurrences
import re

# Find header
header_matches = re.findall(r'<th[^>]*>.*?Free Qty.*?</th>', content, re.IGNORECASE | re.DOTALL)
print(f"Found {len(header_matches)} Free Qty headers:")
for i, match in enumerate(header_matches, 1):
    print(f"{i}. {match[:100]}...")

# Find data cells
cell_matches = re.findall(r'<td[^>]*>.*?sale_free_qty.*?</td>', content, re.IGNORECASE | re.DOTALL)
print(f"\nFound {len(cell_matches)} Free Qty data cells:")
for i, match in enumerate(cell_matches, 1):
    print(f"{i}. {match[:150]}...")

# Check if columns match
print(f"\n{'✓' if len(header_matches) == len(cell_matches) else '✗'} Headers and cells {'match' if len(header_matches) == len(cell_matches) else 'DO NOT match'}")

# Count total columns in header
all_headers = re.findall(r'<th[^>]*class="[^"]*-header"[^>]*>', content)
print(f"\nTotal column headers: {len(all_headers)}")

# Check model field
model_path = r"c:\pharmaproject pratk\WebsiteHostingService\WebsiteHostingService\WebsiteHostingService\core\models.py"
with open(model_path, 'r', encoding='utf-8') as f:
    model_content = f.read()
    if 'sale_free_qty' in model_content:
        print("✓ sale_free_qty field exists in SalesMaster model")
    else:
        print("✗ sale_free_qty field NOT found in model")
