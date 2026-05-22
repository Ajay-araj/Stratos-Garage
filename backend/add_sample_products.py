import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.development')
django.setup()

from products.models import Category, Product, ProductVariant
from sellers.models import Seller
from users.models import User
from inventory.models import Inventory

def run():
    # Ensure an admin/seller user exists
    user, _ = User.objects.get_or_create(username="admin_seller", email="admin_seller@stratosgarage.com", role="seller", defaults={'is_email_verified': True})
    seller, _ = Seller.objects.get_or_create(user=user, defaults={'store_name': "Ajayaraj98's Garage", 'is_verified': True, 'verification_status': 'approved'})

    # Categories
    cat_names = ['Exhaust Systems', 'Riding Jackets', 'Helmets', 'Gloves', 'Handlebars', 'GoPro Mounts', 'Silencers', 'Riding Boots']
    categories = {}
    for name in cat_names:
        c, _ = Category.objects.get_or_create(name=name)
        categories[name] = c

    products = [
        {
            "name": "Akrapovič Slip-On Line (Titanium)",
            "category": categories['Exhaust Systems'],
            "price": 899.99,
            "sku": "EX-AKR-001",
            "desc": "Premium titanium exhaust for enhanced performance and deep sound.",
        },
        {
            "name": "Alpinestars GP Plus R V3 Leather Jacket",
            "category": categories['Riding Jackets'],
            "price": 499.95,
            "sku": "JKT-ALP-001",
            "desc": "Premium full-grain leather racing jacket with superior protection.",
        },
        {
            "name": "Shoei RF-1400 Helmet",
            "category": categories['Helmets'],
            "price": 579.99,
            "sku": "HLM-SHO-001",
            "desc": "Lightweight, aerodynamic, and incredibly quiet full-face helmet.",
        },
        {
            "name": "Dainese Full Metal 6 Gloves",
            "category": categories['Gloves'],
            "price": 429.95,
            "sku": "GLV-DAI-001",
            "desc": "Advanced track gloves featuring titanium and carbon fiber protection.",
        },
        {
            "name": "Renthal Fatbar Carbon",
            "category": categories['Handlebars'],
            "price": 169.95,
            "sku": "HND-REN-001",
            "desc": "High-strength carbon fiber handlebars for ultimate control.",
        },
        {
            "name": "RAM Mounts Tough-Claw GoPro Mount",
            "category": categories['GoPro Mounts'],
            "price": 59.99,
            "sku": "MNT-RAM-001",
            "desc": "Durable and versatile mounting solution for action cameras.",
        },
        {
            "name": "SC-Project CR-T Silencer",
            "category": categories['Silencers'],
            "price": 649.00,
            "sku": "SIL-SCP-001",
            "desc": "MotoGP-derived silencer for extreme weight reduction and performance.",
        },
        {
            "name": "SIDI Mag-1 Racing Boots",
            "category": categories['Riding Boots'],
            "price": 549.99,
            "sku": "BOT-SID-001",
            "desc": "Ultra-lightweight micro-adjustable racing boots for peak track performance.",
        }
    ]

    for p in products:
        prod, created = Product.objects.get_or_create(
            name=p['name'],
            defaults={
                'seller': seller,
                'category': p['category'],
                'description': p['desc'],
                'short_description': p['desc'][:100],
                'base_price': p['price'],
                'is_active': True
            }
        )
        if created:
            variant, _ = ProductVariant.objects.get_or_create(
                product=prod,
                sku=p['sku'],
                defaults={'price': p['price']}
            )
            Inventory.objects.get_or_create(
                variant=variant,
                defaults={'quantity_available': 50}
            )

    print("Sample products added successfully.")

if __name__ == '__main__':
    run()
