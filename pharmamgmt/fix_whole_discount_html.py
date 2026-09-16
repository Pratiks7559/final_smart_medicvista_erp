import re

# ── Helper ───────────────────────────────────────────────────────────────────
def apply_whole_discount_js(whole_disc_input_id, whole_disc_mode_name, whole_disc_type_name,
                             whole_disc_section_id, disc_mode_radio_name, disc_mode_whole_val,
                             recalc_fn):
    """Return JS snippet that sets whole discount from challan data."""
    return (
        f"    // Apply whole discount from challan if present\n"
        f"    if (data.whole_discount_amount && data.whole_discount_amount > 0) {{\n"
        f"        // Switch to whole discount mode\n"
        f"        const wholeRadio = document.querySelector('input[name=\"{disc_mode_radio_name}\"][value=\"{disc_mode_whole_val}\"]');\n"
        f"        if (wholeRadio) {{\n"
        f"            wholeRadio.checked = true;\n"
        f"            wholeRadio.dispatchEvent(new Event('change'));\n"
        f"        }}\n"
        f"        const flatRadio = document.querySelector('input[name=\"{whole_disc_type_name}\"][value=\"flat\"]');\n"
        f"        if (flatRadio) flatRadio.checked = true;\n"
        f"        const discInput = document.getElementById('{whole_disc_input_id}');\n"
        f"        if (discInput) {{\n"
        f"            discInput.value = data.whole_discount_amount.toFixed(2);\n"
        f"            discInput.dispatchEvent(new Event('input'));\n"
        f"        }}\n"
        f"    }}\n"
    )

# ── 1. combined_sales_invoice_form.html (customer) ───────────────────────────
sales_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\templates\sales\combined_sales_invoice_form.html'
with open(sales_path, 'r', encoding='utf-8') as f:
    sales = f.read()

# In pullSelectedChallans: after fillChallanProducts(data.products); add whole discount
old_sales = "            fillChallanProducts(data.products);\n            closePullChallanDialog();"
new_sales = (
    "            fillChallanProducts(data.products);\n"
    "            // Apply whole discount from challan if present\n"
    "            if (data.whole_discount_amount && data.whole_discount_amount > 0) {\n"
    "                const wholeRadio = document.querySelector('input[name=\"discount_mode\"][value=\"whole\"]');\n"
    "                if (wholeRadio) { wholeRadio.checked = true; wholeRadio.dispatchEvent(new Event('change')); }\n"
    "                const flatRadio = document.querySelector('input[name=\"sales_whole_disc_type\"][value=\"flat\"]');\n"
    "                if (flatRadio) flatRadio.checked = true;\n"
    "                const discInput = document.getElementById('salesWholeDiscountInput');\n"
    "                if (discInput) { discInput.value = data.whole_discount_amount.toFixed(2); discInput.dispatchEvent(new Event('input')); }\n"
    "            }\n"
    "            closePullChallanDialog();"
)
if old_sales in sales:
    sales = sales.replace(old_sales, new_sales, 1)
    with open(sales_path, 'w', encoding='utf-8') as f:
        f.write(sales)
    print('combined_sales_invoice_form.html: REPLACED OK')
else:
    print('combined_sales_invoice_form.html: NOT FOUND')
    idx = sales.find('fillChallanProducts(data.products)')
    print(repr(sales[max(0,idx-20):idx+120]))

# ── 2. combined_invoice_form.html (supplier) ─────────────────────────────────
inv_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\templates\purchases\combined_invoice_form.html'
with open(inv_path, 'r', encoding='utf-8') as f:
    inv = f.read()

# In pullSelectedChallans: after all addProductRowFromChallan calls, before calculateInvoiceTotal
old_inv = (
    "            // Mark as from challan\n"
    "            document.getElementById('isFromChallan').value = 'true';\n"
    "            \n"
    "            // Calculate invoice total immediately\n"
    "            calculateInvoiceTotal();"
)
new_inv = (
    "            // Mark as from challan\n"
    "            document.getElementById('isFromChallan').value = 'true';\n"
    "            \n"
    "            // Apply whole discount from challan if present\n"
    "            if (data.whole_discount_amount && data.whole_discount_amount > 0) {\n"
    "                const wholeRadio = document.querySelector('input[name=\"discount_mode\"][value=\"whole\"]');\n"
    "                if (wholeRadio) { wholeRadio.checked = true; wholeRadio.dispatchEvent(new Event('change')); }\n"
    "                const flatRadio = document.querySelector('input[name=\"whole_disc_type\"][value=\"flat\"]');\n"
    "                if (flatRadio) flatRadio.checked = true;\n"
    "                const discInput = document.getElementById('wholeDiscountAmount');\n"
    "                if (discInput) { discInput.value = data.whole_discount_amount.toFixed(2); discInput.dispatchEvent(new Event('input')); }\n"
    "            }\n"
    "\n"
    "            // Calculate invoice total immediately\n"
    "            calculateInvoiceTotal();"
)
if old_inv in inv:
    inv = inv.replace(old_inv, new_inv, 1)
    with open(inv_path, 'w', encoding='utf-8') as f:
        f.write(inv)
    print('combined_invoice_form.html: REPLACED OK')
else:
    print('combined_invoice_form.html: NOT FOUND')
    idx = inv.find("isFromChallan")
    print(repr(inv[max(0,idx-20):idx+200]))
