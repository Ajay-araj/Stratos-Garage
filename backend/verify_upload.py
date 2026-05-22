import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.base')
django.setup()

from django.test import RequestFactory
from products.views import ProductCreateView
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from products.models import Category

User = get_user_model()
user, _ = User.objects.get_or_create(email='test_seller@test.com', defaults={'password': 'test', 'role': 'seller', 'is_active': True})

cat, _ = Category.objects.get_or_create(name='Test Cat', slug='test-cat')

rf = RequestFactory()
data = {
    'name': 'Test Product Mult',
    'category': cat.id,
    'brand': 'TestBrand',
    'description': 'Test desc',
    'short_description': 'short desc',
    'price': '99.99',
    'stock': '10',
    'sku': 'SKU-TEST-123'
}

img = SimpleUploadedFile(name='test_img.jpg', content=b'fake image data', content_type='image/jpeg')
data['images'] = img

req = rf.post('/api/products/add/', data=data)
req.user = user

view = ProductCreateView.as_view()
response = view(req)
print(f"Status: {response.status_code}")
if response.status_code != 201:
    print(f"Data: {response.data}")
else:
    print("Product Created Successfully with Variant and Images")
