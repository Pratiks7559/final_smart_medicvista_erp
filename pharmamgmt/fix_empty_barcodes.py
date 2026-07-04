"""
Run this once to fix existing empty-string barcodes in the database.
Empty strings on a unique column cause duplicate entry errors.

Usage: python manage.py shell < fix_empty_barcodes.py
  OR:  python manage.py runscript fix_empty_barcodes  (if django-extensions installed)
"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharmamgmt.settings')
django.setup()

from core.models import ProductMaster

updated = ProductMaster.objects.filter(product_barcode='').update(product_barcode=None)
print(f"Fixed {updated} products: empty barcode '' → NULL")
