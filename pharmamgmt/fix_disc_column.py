path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\templates\purchases\combined_invoice_form.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "    // Show/hide product-wise discount column\n    const discCells = document.querySelectorAll('.ci-th-discount, .disc-cell');\n    discCells.forEach(el => el.style.display = mode === 'whole' ? 'none' : '');"

new = "    // Grey-out product-wise discount column (do NOT hide — hiding causes table column compression)\n    const discCells = document.querySelectorAll('.ci-th-discount, .disc-cell');\n    discCells.forEach(el => {\n        el.style.opacity = mode === 'whole' ? '0.35' : '1';\n        el.style.pointerEvents = mode === 'whole' ? 'none' : '';\n    });"

if old in content:
    content = content.replace(old, new, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('REPLACED OK')
else:
    print('NOT FOUND')
    idx = content.find('Show/hide product-wise discount')
    print(repr(content[max(0,idx-10):idx+200]))
