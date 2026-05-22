import os, django, traceback
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Stratosgarage.settings.base')
django.setup()

from django.test import Client
from users.models import User

client = Client()
u = User.objects.filter(is_superuser=True).first()
if u:
    client.force_login(u)
    try:
        response = client.get('/admin/users/user/')
        print(f"Status: {response.status_code}")
    except Exception as e:
        traceback.print_exc()
