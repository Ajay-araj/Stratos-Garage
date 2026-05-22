import sys

# We are in manage.py shell
from products.models import Product, Category

# 1. Define allowed categories
allowed_slugs = ['motorcycles', 'riding-gear', 'performance-parts', 'racing-collection']

# Create or update the 4 allowed categories
c_moto, _ = Category.objects.get_or_create(slug='motorcycles', defaults={'name': 'Motorcycle'})
c_gear, _ = Category.objects.get_or_create(slug='riding-gear', defaults={'name': 'Riding Gear'})
c_perf, _ = Category.objects.get_or_create(slug='performance-parts', defaults={'name': 'Performance Parts'})
c_race, _ = Category.objects.get_or_create(slug='racing-collection', defaults={'name': 'Racing Collection'})

c_moto.name = 'Motorcycle'
c_gear.name = 'Riding Gear'
c_perf.name = 'Performance Parts'
c_race.name = 'Racing Collection'
c_moto.save()
c_gear.save()
c_perf.save()
c_race.save()

# 2. Get all bikes (from any motorcycle-like category)
bike_slugs = ['motorcycles', 'sport-bikes', 'super-bikes', 'cruisers', 'adventure-bikes']
all_bikes = Product.objects.filter(category__slug__in=bike_slugs)

bike_to_keep = None
for b in all_bikes:
    if 'ducati' in b.name.lower() or 'panigale' in b.name.lower() or 'v4' in b.name.lower() or 'bmw' in b.name.lower() or 'ninja' in b.name.lower() or 'yamaha' in b.name.lower():
        bike_to_keep = b
        break

if not bike_to_keep and all_bikes.exists():
    bike_to_keep = all_bikes.first()

if bike_to_keep:
    # Ensure it's in the main Motorcycle category
    bike_to_keep.category = c_moto
    bike_to_keep.save()
    print("Kept premium bike:", bike_to_keep.name.encode('utf-8', 'ignore'))

# Delete all other bikes
for b in all_bikes:
    if bike_to_keep and b.id != bike_to_keep.id:
        print("Deleting extra bike:", b.name.encode('utf-8', 'ignore'))
        b.delete()

# 3. Clean up other products
# Move items to correct categories if needed, and delete random stuff
for p in Product.objects.exclude(category__slug__in=allowed_slugs):
    # e.g., exhausts, silencers -> performance-parts
    # helmets, gloves, riding-jackets, riding-boots -> riding-gear
    # others -> delete
    slug = p.category.slug if p.category else ''
    if slug in ['exhaust-systems', 'silencers', 'performance-upgrades']:
        p.category = c_perf
        p.save()
        print("Moved to Performance Parts:", p.name.encode('utf-8', 'ignore'))
    elif slug in ['helmets', 'gloves', 'riding-jackets', 'riding-boots']:
        p.category = c_gear
        p.save()
        print("Moved to Riding Gear:", p.name.encode('utf-8', 'ignore'))
    else:
        if not (bike_to_keep and p.id == bike_to_keep.id):
            print("Deleting unnecessary product:", p.name.encode('utf-8', 'ignore'))
            p.delete()

# 4. Remove unwanted categories
for c in Category.objects.exclude(slug__in=allowed_slugs):
    print("Deleting category:", c.name.encode('utf-8', 'ignore'))
    c.delete()

print("Database cleaned successfully!")
