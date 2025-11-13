import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.models import CatalyticConverter, Manufacturer

print('=== Manufacturers ===')
for m in Manufacturer.objects.all()[:10]:
    print(f'- {m.name}')

print('\n=== Sample Converters ===')
for c in CatalyticConverter.objects.all()[:10]:
    print(f'EO: {c.executive_order}, Make: {c.make}, Year: {c.model_year_start}-{c.model_year_end}, Mfr: {c.manufacturer.name[:50]}')

print(f'\nTotal Manufacturers: {Manufacturer.objects.count()}')
print(f'Total Converters: {CatalyticConverter.objects.count()}')

print('\n=== Unique Makes ===')
makes = CatalyticConverter.objects.exclude(make__isnull=True).exclude(make='').values_list('make', flat=True).distinct()
print(list(makes)[:20])
