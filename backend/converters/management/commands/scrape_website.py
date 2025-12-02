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
