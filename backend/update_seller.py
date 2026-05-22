import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.base')
django.setup()

from sellers.models import Seller
try:
    seller = Seller.objects.get(store_name='Stratos Premium Gear')
    seller.store_name = "Ajayaraj98's Garage"
    seller.save()
    print("Updated existing seller.")
except Seller.DoesNotExist:
    print("Seller not found.")
