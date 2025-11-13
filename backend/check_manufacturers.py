import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.models import Manufacturer

from converters.models import CatalyticConverter

print('=== Manufacturers ===')
for m in Manufacturer.objects.all():
    count = CatalyticConverter.objects.filter(manufacturer=m).count()
    print(f'  - {m.name} ({count} converters)')

print(f'\nTotal Manufacturers: {Manufacturer.objects.count()}')
