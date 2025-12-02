"""
Django management command to scrape CARB data
Usage: python manage.py scrape_carb_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from converters.models import Manufacturer, CatalyticConverter
from converters.scraper import CARBScraper, CARBDataProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape CARB catalytic converter data from website and PDF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='pdf',
            choices=['pdf', 'website', 'both'],
            help='Data source to scrape (pdf, website, or both)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of records to import (for testing)'
        )
        parser.add_argument(
            '--use-local',
            action='store_true',
            default=True,
            help='Use local PDF file instead of downloading (default: True)'
        )
        parser.add_argument(
            '--remote',
            action='store_true',
            default=False,
            help='Download PDF from remote URL instead of using local file'
        )

    def handle(self, *args, **options):
        source = options['source']
        limit = options['limit']
        use_local = not options['remote']  # Use local unless --remote flag is set

        self.stdout.write(self.style.SUCCESS(f'Starting CARB data scraping from {source}...'))
        if use_local:
            self.stdout.write('Using local PDF file')
        else:
            self.stdout.write('Downloading PDF from remote URL')

        scraper = CARBScraper(use_local=use_local)
        processor = CARBDataProcessor()
        all_data = []

        # Scrape based on source
        if source in ['pdf', 'both']:
            self.stdout.write('Scraping PDF data...')
            pdf_data = scraper.scrape_pdf()
            all_data.extend(pdf_data)
            self.stdout.write(self.style.SUCCESS(f'Found {len(pdf_data)} records in PDF'))

        if source in ['website', 'both']:
            self.stdout.write('Scraping website data...')
            website_data = scraper.scrape_website()
            all_data.extend(website_data)
            self.stdout.write(self.style.SUCCESS(f'Found {len(website_data)} records on website'))

        # Apply limit if specified
        if limit:
            all_data = all_data[:limit]
            self.stdout.write(f'Limited to {limit} records')

        # Process and import data
        self.stdout.write(f'Processing {len(all_data)} records...')

        created_count = 0
        updated_count = 0
        error_count = 0

        for raw_data in all_data:
            try:
                # Clean data
                cleaned_data = processor.clean_converter_data(raw_data)

                # Validate data
                if not processor.validate_converter_data(cleaned_data):
                    self.stdout.write(
                        self.style.WARNING(f'Skipping invalid record: {cleaned_data}')
                    )
                    error_count += 1
                    continue

                # Get or create manufacturer
                manufacturer_name = cleaned_data.get('manufacturer_name', 'Unknown')
                manufacturer_contact = cleaned_data.get('manufacturer_contact')

                manufacturer, created = Manufacturer.objects.get_or_create(
                    name=manufacturer_name,
                    defaults={'contact_info': manufacturer_contact} if manufacturer_contact else {}
                )

                # Update contact_info if manufacturer exists and has new contact info
                if not created and manufacturer_contact and manufacturer.contact_info != manufacturer_contact:
                    manufacturer.contact_info = manufacturer_contact
                    manufacturer.save()

                # Extract all key fields for exact matching
                executive_order = cleaned_data.get('executive_order')
                test_group = cleaned_data.get('test_group') or ''
                series_model = cleaned_data.get('series_model') or ''
                product_name = cleaned_data.get('product_name') or ''
                make = cleaned_data.get('make') or ''
                model = cleaned_data.get('model') or ''
                model_year_start = cleaned_data.get('model_year_start')
                model_year_end = cleaned_data.get('model_year_end')
                vehicle_class = cleaned_data.get('vehicle_class') or ''
                engine_size = cleaned_data.get('engine_size') or ''
                cert_level = cleaned_data.get('cert_level') or ''
                application_type = cleaned_data.get('application_type') or ''
                converter_location = cleaned_data.get('converter_location') or ''
                converter_type = cleaned_data.get('converter_type') or ''
                quantity = cleaned_data.get('quantity')

                # Prepare defaults (fields not used in lookup)
                defaults = {
                    'product_name': product_name,
                    'eo_date': cleaned_data.get('eo_date'),
                    'last_scraped': timezone.now(),
                }

                # Use get_or_create with ALL distinguishing fields
                # This ensures exact match - first run inserts all, subsequent runs skip exact duplicates
                converter, created = CatalyticConverter.objects.get_or_create(
                    manufacturer=manufacturer,
                    executive_order=executive_order,
                    test_group=test_group,
                    series_model=series_model,
                    make=make,
                    model=model,
                    model_year_start=model_year_start,
                    model_year_end=model_year_end,
                    vehicle_class=vehicle_class,
                    engine_size=engine_size,
                    cert_level=cert_level,
                    application_type=application_type,
                    converter_location=converter_location,
                    converter_type=converter_type,
                    quantity=quantity,
                    defaults=defaults
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'Error processing record: {e}')
                )
                logger.exception(f'Error processing record: {raw_data}')

        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Scraping Complete ==='))
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'Errors: {error_count}'))

        total_converters = CatalyticConverter.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal converters in database: {total_converters}')
        )
