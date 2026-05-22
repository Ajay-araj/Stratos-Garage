from products.models import Category, Product
from django.utils.text import slugify

# Mapping based on user request
main_cats = {
    'Motorcycles': ['Sport Bikes', 'Super Bikes', 'Cruisers', 'Adventure Bikes'],
    'Riding Gear': ['Helmets', 'Gloves', 'Riding Jackets', 'Riding Boots'],
    'Performance Parts': ['Exhaust Systems', 'Silencers', 'Handlebars', 'Performance Upgrades'],
    'Accessories': ['GoPro Mounts', 'Phone Mounts', 'Tools', 'Bike Accessories']
}

for main, subs in main_cats.items():
    slug = slugify(main)
    parent, _ = Category.objects.get_or_create(name=main, defaults={'slug': slug})
    
    parent.parent = None
    parent.slug = slug
    parent.is_active = True
    parent.save()

    for sub in subs:
        sub_slug = slugify(sub)
        sub_cat, _ = Category.objects.get_or_create(name=sub, defaults={'slug': sub_slug, 'parent': parent})
        
        sub_cat.parent = parent
        sub_cat.slug = sub_slug
        sub_cat.is_active = True
        sub_cat.save()

# Let's map existing products to the new categories to make the pages work!
# Find existing products by name and assign them
for p in Product.objects.all():
    lname = p.name.lower()
    if 'helmet' in lname:
        cat = Category.objects.get(name='Helmets')
        p.category = cat
        p.save()
    elif 'exhaust' in lname or 'akrapovic' in lname:
        cat = Category.objects.get(name='Exhaust Systems')
        p.category = cat
        p.save()
    elif 'jacket' in lname:
        cat = Category.objects.get(name='Riding Jackets')
        p.category = cat
        p.save()
    elif 'glove' in lname:
        cat = Category.objects.get(name='Gloves')
        p.category = cat
        p.save()
    elif 'boot' in lname or 'shoes' in lname:
        cat = Category.objects.get(name='Riding Boots')
        p.category = cat
        p.save()
    elif 'mount' in lname or 'gopro' in lname:
        cat = Category.objects.get(name='GoPro Mounts')
        p.category = cat
        p.save()
    elif 'handlebar' in lname:
        cat = Category.objects.get(name='Handlebars')
        p.category = cat
        p.save()
    elif 'silencer' in lname:
        cat = Category.objects.get(name='Silencers')
        p.category = cat
        p.save()
    elif 'bike' in lname or 'ducati' in lname or 'ninja' in lname or 'yamaha' in lname:
        cat = Category.objects.get(name='Super Bikes')
        p.category = cat
        p.save()
        
print("Categories updated successfully!")
