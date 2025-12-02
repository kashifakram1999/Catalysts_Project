"""
Django management command to remove manufacturers with contact info and their data
Usage: python manage.py remove_manufacturers_with_contact
"""

from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from converters.models import Manufacturer, CatalyticConverter


class Command(BaseCommand):
    help = 'Remove manufacturers that have contact info and all their associated converter data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompting'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        # Find manufacturers with contact info (not null and not empty)
        manufacturers_with_contact = Manufacturer.objects.filter(
            Q(contact_info__isnull=False) & ~Q(contact_info='')
        ).annotate(
            converter_count=Count('converters')
        )

        if not manufacturers_with_contact.exists():
            self.stdout.write(
                self.style.SUCCESS('\nNo manufacturers with contact info found.')
            )
            return

        # Calculate totals
        total_manufacturers = manufacturers_with_contact.count()
        total_converters = sum(m.converter_count for m in manufacturers_with_contact)

        # Display what will be deleted
        self.stdout.write(
            self.style.WARNING(f'\nFound {total_manufacturers} manufacturer(s) with contact info:')
        )
        self.stdout.write('=' * 80)

        for manufacturer in manufacturers_with_contact:
            self.stdout.write(
                f'\n  • {manufacturer.name}'
            )
            self.stdout.write(
                f'    Contact: {manufacturer.contact_info[:100]}{"..." if len(manufacturer.contact_info) > 100 else ""}'
            )
            self.stdout.write(
                f'    Associated converters: {manufacturer.converter_count}'
            )

        self.stdout.write('\n' + '=' * 80)
        self.stdout.write(
            self.style.WARNING(f'\nThis will delete:')
        )
        self.stdout.write(f'  - {total_manufacturers} Manufacturer(s)')
        self.stdout.write(f'  - {total_converters} Catalytic Converter(s)')

        # Dry run check
        if options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS('\n[DRY RUN] No data was deleted.')
            )
            return

        # Confirmation
        if not options['confirm']:
            confirm = input('\nAre you sure you want to delete these manufacturers and their data? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return

        # Delete manufacturers (cascade will delete associated converters)
        self.stdout.write('\nDeleting manufacturers and their converters...')

        deleted_info = manufacturers_with_contact.delete()
        # deleted_info is a tuple: (total_deleted, {model_name: count})

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Successfully deleted:')
        )
        self.stdout.write(
            self.style.SUCCESS(f'  - {deleted_info[1].get("converters.Manufacturer", 0)} manufacturer(s)')
        )
        self.stdout.write(
            self.style.SUCCESS(f'  - {deleted_info[1].get("converters.CatalyticConverter", 0)} converter(s)')
        )

        # Show remaining counts
        remaining_manufacturers = Manufacturer.objects.count()
        remaining_converters = CatalyticConverter.objects.count()

        self.stdout.write(
            self.style.SUCCESS(f'\nRemaining in database:')
        )
        self.stdout.write(f'  - {remaining_manufacturers} manufacturer(s)')
        self.stdout.write(f'  - {remaining_converters} converter(s)')

        self.stdout.write(
            self.style.SUCCESS('\nCleanup completed successfully!')
        )
