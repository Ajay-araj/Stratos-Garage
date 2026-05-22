import os
import urllib.request

base_dir = r"c:\Project\Stratos Garage\frontend\public\images\categories"
os.makedirs(base_dir, exist_ok=True)

images = {
    'motorcycles-banner.jpg': 'https://images.unsplash.com/photo-1558981403-c5f9899a28bc?q=80&w=2000&auto=format&fit=crop',
    'sport-bikes-banner.jpg': 'https://images.unsplash.com/photo-1568772585407-9361f9bf3a87?q=80&w=2000&auto=format&fit=crop',
    'super-bikes-banner.jpg': 'https://images.unsplash.com/photo-1591637333184-19aa84b3e01f?q=80&w=2000&auto=format&fit=crop',
    'cruisers-banner.jpg': 'https://images.unsplash.com/photo-1558980663-3685c1d673c4?q=80&w=2000&auto=format&fit=crop',
    'adventure-bikes-banner.jpg': 'https://images.unsplash.com/photo-1614217316089-631d8f58b4da?q=80&w=2000&auto=format&fit=crop',

    'riding-gear-banner.jpg': 'https://images.unsplash.com/photo-1558981359-219d6364c9c8?q=80&w=2070&auto=format&fit=crop',
    'helmets-banner.jpg': 'https://images.unsplash.com/photo-1557342629-9e87900b1a13?q=80&w=2000&auto=format&fit=crop',
    'gloves-banner.jpg': 'https://images.unsplash.com/photo-1518331483807-f6abc1e749db?q=80&w=2000&auto=format&fit=crop',
    'riding-jackets-banner.jpg': 'https://images.unsplash.com/photo-1521223830155-f6cb10b8fcb3?q=80&w=2000&auto=format&fit=crop',
    'riding-boots-banner.jpg': 'https://images.unsplash.com/photo-1517783999520-f068d7431a60?q=80&w=2000&auto=format&fit=crop',

    'performance-parts-banner.jpg': 'https://images.unsplash.com/photo-1486262715619-67b85e0b08d3?q=80&w=2072&auto=format&fit=crop',
    'exhaust-systems-banner.jpg': 'https://images.unsplash.com/photo-1589255653556-9d21cb50c2ce?q=80&w=2000&auto=format&fit=crop',
    'silencers-banner.jpg': 'https://images.unsplash.com/photo-1582875955075-8025cb736bd9?q=80&w=2000&auto=format&fit=crop',
    'handlebars-banner.jpg': 'https://images.unsplash.com/photo-1611796120894-37542daffc51?q=80&w=2000&auto=format&fit=crop',
    'performance-upgrades-banner.jpg': 'https://images.unsplash.com/photo-1596700683072-019b88cf2436?q=80&w=2000&auto=format&fit=crop',

    'accessories-banner.jpg': 'https://images.unsplash.com/photo-1599819811279-d5ad9cccf838?q=80&w=2000&auto=format&fit=crop',
    'gopro-mounts-banner.jpg': 'https://images.unsplash.com/photo-1563212046-608f1b63cc4f?q=80&w=2000&auto=format&fit=crop',
    'phone-mounts-banner.jpg': 'https://images.unsplash.com/photo-1605335123019-b22e16b9b3cc?q=80&w=2000&auto=format&fit=crop',
    'tools-banner.jpg': 'https://images.unsplash.com/photo-1530124566582-a618bc2615dc?q=80&w=2000&auto=format&fit=crop',
    'bike-accessories-banner.jpg': 'https://images.unsplash.com/photo-1558980394-0a37c36395dc?q=80&w=2000&auto=format&fit=crop',

    'default-category-banner.jpg': 'https://images.unsplash.com/photo-1558981806-ec527fa84c39?q=80&w=2000&auto=format&fit=crop'
}

req_headers = {
    'User-Agent': 'Mozilla/5.0'
}

for filename, url in images.items():
    filepath = os.path.join(base_dir, filename)
    if not os.path.exists(filepath):
        print(f"Downloading {filename}...")
        try:
            req = urllib.request.Request(url, headers=req_headers)
            with urllib.request.urlopen(req) as response, open(filepath, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"Failed to download {filename}: {e}")
    else:
        print(f"{filename} already exists.")

print("All done!")
