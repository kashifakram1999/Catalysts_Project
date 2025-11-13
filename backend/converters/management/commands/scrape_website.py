"""
Django management command to scrape CARB data from the website
Usage: python manage.py scrape_website
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from converters.models import Manufacturer, CatalyticConverter
from converters.website_scraper import CARBWebsiteScraper
from converters.scraper import CARBDataProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape CARB catalytic converter data from the interactive website using Selenium'

    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode (default: True)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of manufacturers to scrape (for testing)'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=10,
            help='Timeout for element waits in seconds (default: 10)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode: scrape only 2 manufacturers'
        )

    def handle(self, *args, **options):
        headless = options['headless']
        limit = options['limit']
        timeout = options['timeout']
        test_mode = options['test']

        if test_mode:
            limit = 2
            self.stdout.write(self.style.WARNING('Running in TEST MODE: limiting to 2 manufacturers'))

        self.stdout.write(self.style.SUCCESS('Starting CARB website scraping...'))
        self.stdout.write(f'Settings: Headless={headless}, Timeout={timeout}s, Limit={limit or "None"}')

        # Initialize scraper
        scraper = CARBWebsiteScraper(headless=headless, timeout=timeout)
        processor = CARBDataProcessor()

        # Scrape data
        self.stdout.write('\nScraping website data...')
        try:
            all_data = scraper.scrape_all_data(limit_manufacturers=limit)
            self.stdout.write(self.style.SUCCESS(f'Found {len(all_data)} records from website'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error scraping website: {e}'))
            logger.exception('Website scraping failed')
            return

        if not all_data:
            self.stdout.write(self.style.WARNING('No data found. Please check:'))
            self.stdout.write('  1. Chrome/Chromium is installed')
            self.stdout.write('  2. ChromeDriver is installed and in PATH')
            self.stdout.write('  3. Website structure hasn\'t changed')
            return

        # Process and import data
        self.stdout.write(f'\nProcessing {len(all_data)} records...')

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

                # Prepare converter data
                converter_data = {
                    'manufacturer': manufacturer,
                    'executive_order': cleaned_data.get('executive_order'),
                    'series_model': cleaned_data.get('series_model'),
                    'product_name': cleaned_data.get('product_name'),
                    'model_year_start': cleaned_data.get('model_year_start'),
                    'model_year_end': cleaned_data.get('model_year_end'),
                    'make': cleaned_data.get('make'),
                    'model': cleaned_data.get('model'),
                    'vehicle_class': cleaned_data.get('vehicle_class'),
                    'engine_size': cleaned_data.get('engine_size'),
                    'test_group': cleaned_data.get('test_group'),
                    'cert_level': cleaned_data.get('cert_level'),
                    'application_type': cleaned_data.get('application_type'),
                    'converter_location': cleaned_data.get('converter_location'),
                    'converter_type': cleaned_data.get('converter_type'),
                    'quantity': cleaned_data.get('quantity'),
                    'eo_date': cleaned_data.get('eo_date'),
                    'last_scraped': timezone.now(),
                }

                # Update or create converter
                converter, created = CatalyticConverter.objects.update_or_create(
                    executive_order=cleaned_data.get('executive_order'),
                    manufacturer=manufacturer,
                    defaults=converter_data
                )

                if created:
                    created_count += 1
                    self.stdout.write('.', ending='')
                else:
                    updated_count += 1
                    self.stdout.write('u', ending='')

                # Flush output every 50 records
                if (created_count + updated_count) % 50 == 0:
                    self.stdout.flush()

            except Exception as e:
                error_count += 1
                self.stdout.write('x', ending='')
                logger.exception(f'Error processing record: {raw_data}')

        # Summary
        self.stdout.write('\n\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('=== Website Scraping Complete ==='))
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS(f'Created: {created_count}'))
        self.stdout.write(self.style.SUCCESS(f'Updated: {updated_count}'))
        if error_count > 0:
            self.stdout.write(self.style.WARNING(f'Errors: {error_count}'))

        total_converters = CatalyticConverter.objects.count()
        self.stdout.write(
            self.style.SUCCESS(f'\nTotal converters in database: {total_converters}')
        )

        if test_mode:
            self.stdout.write('\n' + self.style.WARNING('TEST MODE completed successfully!'))
            self.stdout.write('To scrape all data, run: python manage.py scrape_website')
