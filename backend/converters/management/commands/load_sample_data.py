"""
Load sample CARB catalytic converter data for testing
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from converters.models import Manufacturer, CatalyticConverter
from datetime import date


class Command(BaseCommand):
    help = 'Load sample catalytic converter data for development/testing'

    def handle(self, *args, **options):
        self.stdout.write('Loading sample data...')

        # Create sample manufacturers
        magnaflow, _ = Manufacturer.objects.get_or_create(name='MagnaFlow')
        walker, _ = Manufacturer.objects.get_or_create(name='Walker')
        eastern, _ = Manufacturer.objects.get_or_create(name='Eastern Catalytic')

        # Sample data based on typical CARB records
        sample_converters = [
            {
                'manufacturer': magnaflow,
                'executive_order': 'D-193-123',
                'product_name': 'MagnaFlow Direct-Fit Catalytic Converter',
                'series_model': '49-STATE',
                'model_year_start': 2005,
                'model_year_end': 2010,
                'make': 'Honda',
                'model': 'Civic',
                'vehicle_class': 'PC',
                'engine_size': '1.8L',
                'test_group': 'FHNXV01.8M5A',
                'cert_level': 'LEV II',
                'application_type': 'Direct-Fit',
                'converter_location': 'Front',
                'converter_type': 'Three-Way',
                'quantity': 1,
                'eo_date': date(2005, 3, 15),
            },
            {
                'manufacturer': magnaflow,
                'executive_order': 'D-193-124',
                'product_name': 'MagnaFlow Catalytic Converter',
                'model_year_start': 2006,
                'model_year_end': 2011,
                'make': 'Toyota',
                'model': 'Camry',
                'vehicle_class': 'PC',
                'engine_size': '2.4L',
                'test_group': 'GTNXV02.4004',
                'cert_level': 'ULEV',
                'application_type': 'Direct-Fit',
                'converter_location': 'Front',
                'converter_type': 'Three-Way',
                'quantity': 1,
                'eo_date': date(2006, 5, 20),
            },
            {
                'manufacturer': walker,
                'executive_order': 'D-256-89',
                'product_name': 'Walker Ultra EPA Converter',
                'model_year_start': 2008,
                'model_year_end': 2012,
                'make': 'Ford',
                'model': 'F-150',
                'vehicle_class': 'LDT',
                'engine_size': '5.4L',
                'test_group': 'FFRXT05.4V8A',
                'cert_level': 'Tier 2 Bin 5',
                'application_type': 'Direct-Fit',
                'converter_location': 'Rear',
                'converter_type': 'Three-Way',
                'quantity': 2,
                'eo_date': date(2008, 8, 10),
            },
            {
                'manufacturer': eastern,
                'executive_order': 'D-345-67',
                'product_name': 'Eastern Catalytic Converter',
                'model_year_start': 2010,
                'model_year_end': 2015,
                'make': 'Chevrolet',
                'model': 'Silverado',
                'vehicle_class': 'LDT',
                'engine_size': '5.3L',
                'test_group': 'GCPXT05.3V8B',
                'cert_level': 'Tier 2 Bin 5',
                'application_type': 'Direct-Fit',
                'converter_location': 'Manifold',
                'converter_type': 'Three-Way',
                'quantity': 2,
                'eo_date': date(2010, 1, 12),
            },
            {
                'manufacturer': magnaflow,
                'executive_order': 'D-456-78',
                'product_name': 'MagnaFlow Universal Converter',
                'model_year_start': 2000,
                'model_year_end': 2020,
                'make': 'Universal',
                'vehicle_class': 'PC',
                'engine_size': 'Various',
                'cert_level': 'LEV II',
                'application_type': 'Universal',
                'converter_type': 'Three-Way',
                'quantity': 1,
                'eo_date': date(2015, 6, 1),
            },
            {
                'manufacturer': walker,
                'executive_order': 'D-567-89',
                'product_name': 'Walker CalCat Converter',
                'model_year_start': 2012,
                'model_year_end': 2017,
                'make': 'Nissan',
                'model': 'Altima',
                'vehicle_class': 'PC',
                'engine_size': '2.5L',
                'test_group': 'NNSXV02.5L4A',
                'cert_level': 'ULEV',
                'application_type': 'Direct-Fit',
                'converter_location': 'Front',
                'converter_type': 'Three-Way',
                'quantity': 1,
                'eo_date': date(2012, 4, 15),
            },
            {
                'manufacturer': magnaflow,
                'executive_order': 'D-678-90',
                'product_name': 'MagnaFlow HM Grade Converter',
                'model_year_start': 2015,
                'model_year_end': 2020,
                'make': 'Subaru',
                'model': 'Outback',
                'vehicle_class': 'PC',
                'engine_size': '2.5L',
                'test_group': 'JSBXV02.5L4C',
                'cert_level': 'LEV III',
                'application_type': 'Direct-Fit',
                'converter_location': 'Front',
                'converter_type': 'Three-Way',
                'quantity': 2,
                'eo_date': date(2015, 9, 30),
            },
        ]

        created = 0
        for data in sample_converters:
            _, was_created = CatalyticConverter.objects.get_or_create(
                executive_order=data['executive_order'],
                manufacturer=data['manufacturer'],
                defaults=data
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully loaded {created} sample converters')
        )
        self.stdout.write(
            self.style.SUCCESS(f'Total converters in database: {CatalyticConverter.objects.count()}')
        )
