import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.models import CatalyticConverter

print('=== Records WITH Makes ===')
with_makes = CatalyticConverter.objects.exclude(make__isnull=True).exclude(make='')[:15]
for c in with_makes:
    print(f'EO: {c.executive_order}, Make: {c.make}, Model: {c.model}, Engine: {c.engine_size}, Class: {c.vehicle_class[:40] if c.vehicle_class else "N/A"}')

print(f'\n=== Records WITHOUT Makes (sample) ===')
without_makes = CatalyticConverter.objects.filter(make__isnull=True)[:5]
for c in without_makes:
    print(f'EO: {c.executive_order}, Class: {c.vehicle_class[:60] if c.vehicle_class else "N/A"}')

print(f'\n=== Statistics ===')
print(f'Total converters: {CatalyticConverter.objects.count()}')
print(f'With make: {CatalyticConverter.objects.exclude(make__isnull=True).exclude(make="").count()}')
print(f'With model: {CatalyticConverter.objects.exclude(model__isnull=True).exclude(model="").count()}')
print(f'With engine_size: {CatalyticConverter.objects.exclude(engine_size__isnull=True).exclude(engine_size="").count()}')
print(f'Without make: {CatalyticConverter.objects.filter(make__isnull=True).count()}')
