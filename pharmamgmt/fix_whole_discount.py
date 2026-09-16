import re

# ── 1. combined_invoice_view.py ─────────────────────────────────────────────
ci_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\core\combined_invoice_view.py'
with open(ci_path, 'r', encoding='utf-8') as f:
    ci = f.read()

# Find the get_challan_products return block and add whole_discount
ci_old = re.search(
    r"(        return JsonResponse\(\{\s*'success': True,\s*'products': products_data\s*\}\)\s*\n\s*except Exception as e:\s*\n\s*logger\.error)",
    ci
)
if ci_old:
    ci = ci.replace(ci_old.group(0),
        "        # Sum whole_discount_amount from all selected challans\n"
        "        total_whole_discount = 0.0\n"
        "        try:\n"
        "            from core.models import Challan1 as _C1\n"
        "            for _c in _C1.objects.filter(challan_id__in=challan_ids):\n"
        "                total_whole_discount += float(_c.whole_discount_amount or 0)\n"
        "        except Exception:\n"
        "            pass\n\n"
        "        return JsonResponse({\n"
        "            'success': True,\n"
        "            'products': products_data,\n"
        "            'whole_discount_amount': total_whole_discount\n"
        "        })\n\n"
        "    except Exception as e:\n"
        "        logger.error"
    )
    with open(ci_path, 'w', encoding='utf-8') as f:
        f.write(ci)
    print('combined_invoice_view.py: REPLACED OK')
else:
    print('combined_invoice_view.py: NOT FOUND - trying alternate')
    idx = ci.find("'products': products_data")
    print(repr(ci[max(0,idx-80):idx+200]))

# ── 2. challan_views.py ──────────────────────────────────────────────────────
cv_path = r'c:\wholesaler project\final_smart_medicvista_erp\pharmamgmt\core\challan_views.py'
with open(cv_path, 'r', encoding='utf-8') as f:
    cv = f.read()

cv_old = re.search(
    r"(        return JsonResponse\(\{\s*'success': True,\s*'products': products\s*\}\)\s*\n\s*except Exception as e:\s*\n\s*return JsonResponse\(\{'success': False)",
    cv
)
if cv_old:
    cv = cv.replace(cv_old.group(0),
        "        # Sum whole_discount_amount from all selected challans\n"
        "        total_whole_discount = 0.0\n"
        "        try:\n"
        "            from core.models import CustomerChallan as _CC\n"
        "            for _c in _CC.objects.filter(customer_challan_id__in=challan_ids):\n"
        "                total_whole_discount += float(_c.whole_discount_amount or 0)\n"
        "        except Exception:\n"
        "            pass\n\n"
        "        return JsonResponse({\n"
        "            'success': True,\n"
        "            'products': products,\n"
        "            'whole_discount_amount': total_whole_discount\n"
        "        })\n\n"
        "    except Exception as e:\n"
        "        return JsonResponse({'success': False"
    )
    with open(cv_path, 'w', encoding='utf-8') as f:
        f.write(cv)
    print('challan_views.py: REPLACED OK')
else:
    print('challan_views.py: NOT FOUND - trying alternate')
    idx = cv.find("'products': products")
    print(repr(cv[max(0,idx-80):idx+200]))
