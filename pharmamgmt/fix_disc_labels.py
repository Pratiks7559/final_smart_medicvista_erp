supplier_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\templates\challan\supplier_challan_detail.html'
customer_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\templates\challan\customer_challan_detail.html'

# ── SUPPLIER ─────────────────────────────────────────────────────────────────
with open(supplier_path, 'r', encoding='utf-8') as f:
    s = f.read()

# 1. "Product-wise Discount" label — blue tint
old = '<label style="cursor:pointer;font-size:0.875rem;font-weight:500;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;">\n                                <input type="radio" name="edit_discount_mode" value="product_wise"'
new = '<label style="cursor:pointer;font-size:0.875rem;font-weight:600;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #3b82f6;border-radius:6px;background:#eff6ff;color:#1d4ed8;">\n                                <input type="radio" name="edit_discount_mode" value="product_wise"'
if old in s:
    s = s.replace(old, new, 1)
    print('Supplier: product_wise label colored')
else:
    print('Supplier: product_wise label NOT FOUND')

# 2. "Whole Challan Discount" label — orange tint
old = '<label style="cursor:pointer;font-size:0.875rem;font-weight:500;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;">\n                                <input type="radio" name="edit_discount_mode" value="whole"'
new = '<label style="cursor:pointer;font-size:0.875rem;font-weight:600;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #d97706;border-radius:6px;background:#fffbeb;color:#92400e;">\n                                <input type="radio" name="edit_discount_mode" value="whole"'
if old in s:
    s = s.replace(old, new, 1)
    print('Supplier: whole label colored')
else:
    print('Supplier: whole label NOT FOUND')

# 3. "Flat ₹" label — green tint
old = '<label style="cursor:pointer;font-size:0.82rem;font-weight:600;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;" id="editWholeDiscFlatLabel">\n                                <input type="radio" name="edit_whole_disc_type" value="flat"'
new = '<label style="cursor:pointer;font-size:0.82rem;font-weight:700;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #16a34a;border-radius:6px;background:#f0fdf4;color:#15803d;" id="editWholeDiscFlatLabel">\n                                <input type="radio" name="edit_whole_disc_type" value="flat"'
if old in s:
    s = s.replace(old, new, 1)
    print('Supplier: flat label colored')
else:
    print('Supplier: flat label NOT FOUND')

# 4. "%" label — purple tint
old = '<label style="cursor:pointer;font-size:0.82rem;font-weight:600;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;" id="editWholeDiscPctLabel">\n                                <input type="radio" name="edit_whole_disc_type" value="percentage"'
new = '<label style="cursor:pointer;font-size:0.82rem;font-weight:700;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #7c3aed;border-radius:6px;background:#f5f3ff;color:#6d28d9;" id="editWholeDiscPctLabel">\n                                <input type="radio" name="edit_whole_disc_type" value="percentage"'
if old in s:
    s = s.replace(old, new, 1)
    print('Supplier: pct label colored')
else:
    print('Supplier: pct label NOT FOUND')

with open(supplier_path, 'w', encoding='utf-8') as f:
    f.write(s)

# ── CUSTOMER ─────────────────────────────────────────────────────────────────
with open(customer_path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. "Product-wise Discount" label
old = '<label style="cursor:pointer;font-size:14px;">\n                            <input type="radio" name="edit_discount_mode" id="editDiscModeProductWise"'
new = '<label style="cursor:pointer;font-size:14px;font-weight:600;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #3b82f6;border-radius:6px;background:#eff6ff;color:#1d4ed8;">\n                            <input type="radio" name="edit_discount_mode" id="editDiscModeProductWise"'
if old in c:
    c = c.replace(old, new, 1)
    print('Customer: product_wise label colored')
else:
    print('Customer: product_wise label NOT FOUND')

# 2. "Whole Challan Discount" label
old = '<label style="cursor:pointer;font-size:14px;">\n                            <input type="radio" name="edit_discount_mode" id="editDiscModeWhole"'
new = '<label style="cursor:pointer;font-size:14px;font-weight:600;display:flex;align-items:center;gap:6px;padding:5px 12px;border:1.5px solid #d97706;border-radius:6px;background:#fffbeb;color:#92400e;">\n                            <input type="radio" name="edit_discount_mode" id="editDiscModeWhole"'
if old in c:
    c = c.replace(old, new, 1)
    print('Customer: whole label colored')
else:
    print('Customer: whole label NOT FOUND')

# 3. "Flat ₹" label
old = '<label style="cursor:pointer;font-size:13px;padding:4px 10px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;font-weight:600;">\n                            <input type="radio" name="edit_whole_disc_type" value="flat"'
new = '<label style="cursor:pointer;font-size:13px;font-weight:700;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #16a34a;border-radius:6px;background:#f0fdf4;color:#15803d;">\n                            <input type="radio" name="edit_whole_disc_type" value="flat"'
if old in c:
    c = c.replace(old, new, 1)
    print('Customer: flat label colored')
else:
    print('Customer: flat label NOT FOUND')

# 4. "%" label
old = '<label style="cursor:pointer;font-size:13px;padding:4px 10px;border:1.5px solid #e5e7eb;border-radius:6px;background:#fff;font-weight:600;">\n                            <input type="radio" name="edit_whole_disc_type" value="percentage"'
new = '<label style="cursor:pointer;font-size:13px;font-weight:700;display:flex;align-items:center;gap:4px;padding:4px 10px;border:1.5px solid #7c3aed;border-radius:6px;background:#f5f3ff;color:#6d28d9;">\n                            <input type="radio" name="edit_whole_disc_type" value="percentage"'
if old in c:
    c = c.replace(old, new, 1)
    print('Customer: pct label colored')
else:
    print('Customer: pct label NOT FOUND')

with open(customer_path, 'w', encoding='utf-8') as f:
    f.write(c)
