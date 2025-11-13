#!/usr/bin/env python3
"""
Check what data was scraped
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.models import CatalyticConverter

# Get records for D-182-37
converters = CatalyticConverter.objects.filter(executive_order='D-182-37').order_by('id')[:3]

print("="*80)
print(f"SAMPLE DATA FOR EO: D-182-37")
print("="*80)

for idx, conv in enumerate(converters, 1):
    print(f"\n{'='*80}")
    print(f"RECORD {idx}")
    print(f"{'='*80}")
    print(f"EO Number: {conv.executive_order}")
    print(f"Make: {conv.make}")
    print(f"Model Year: {conv.model_year_start}-{conv.model_year_end}")
    print(f"Model: {conv.model}")
    print(f"Engine Size: {conv.engine_size}")
    print(f"Application Type: {conv.application_type}")
    print(f"Manufacturer: {conv.manufacturer.name if conv.manufacturer else 'None'}")
    print(f"Part Number: {conv.part_number}")
    print(f"Series/Model: {conv.series_model}")
    print(f"Test Group: {conv.test_group}")
    print(f"Cert Level: {conv.cert_level}")
    print(f"Vehicle Class: {conv.vehicle_class}")
    print(f"Total Converters: {conv.quantity}")
    print(f"Catalyst Location: {conv.converter_location}")
    print(f"Catalyst Type: {conv.converter_type}")

print(f"\n{'='*80}")
print(f"Total records for D-182-37: {CatalyticConverter.objects.filter(executive_order='D-182-37').count()}")
print(f"{'='*80}")
