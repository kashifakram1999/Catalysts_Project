"""
Django management command to clear all converter data
Usage: python manage.py clear_data
"""

from django.core.management.base import BaseCommand
from converters.models import Manufacturer, CatalyticConverter


class Command(BaseCommand):
    help = 'Clear all catalytic converter and manufacturer data from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting'
        )

    def handle(self, *args, **options):
        converter_count = CatalyticConverter.objects.count()
        manufacturer_count = Manufacturer.objects.count()

        self.stdout.write(
            self.style.WARNING(f'\nThis will delete:')
        )
        self.stdout.write(f'  - {converter_count} Catalytic Converters')
        self.stdout.write(f'  - {manufacturer_count} Manufacturers')

        if not options['confirm']:
            confirm = input('\nAre you sure you want to delete all data? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Delete all data
        self.stdout.write('\nDeleting data...')

        deleted_converters = CatalyticConverter.objects.all().delete()
        deleted_manufacturers = Manufacturer.objects.all().delete()

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Deleted {deleted_converters[0]} catalytic converter records')
        )
        self.stdout.write(
            self.style.SUCCESS(f'✓ Deleted {deleted_manufacturers[0]} manufacturer records')
        )
        self.stdout.write(
            self.style.SUCCESS('\nDatabase cleared successfully!')
        )
