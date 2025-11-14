"""
TEST Management command to scrape CARB data using the fixed pagination EO scraper
"""

from django.core.management.base import BaseCommand
from converters.eo_scraper_test import CARBEOScraperTest
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

# Create logger for converters app
logger = logging.getLogger('converters')
logger.setLevel(logging.INFO)

# Create console handler
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


class Command(BaseCommand):
    help = 'TEST VERSION: Scrape CARB data by EO numbers with fixed pagination'

    def add_arguments(self, parser):
        parser.add_argument(
            '--headless',
            action='store_true',
            help='Run browser in headless mode (default)',
        )
        parser.add_argument(
            '--visible',
            action='store_true',
            help='Run browser in visible mode (for debugging)',
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=None,
            help='Optional safety limit: max pages per EO (0 or None = scrape all pages)',
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode: scrape only first 3 EO numbers',
        )
        parser.add_argument(
            '--eo-numbers',
            type=str,
            help='Comma-separated list of specific EO numbers to scrape (e.g., D-393-143,D-393-144)',
        )

    def handle(self, *args, **options):
        headless = not options['visible']  # Default is headless unless --visible is set
        pages_per_eo = options['pages'] if options['pages'] else None
        test_mode = options['test']
        eo_numbers_str = options.get('eo_numbers')

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('TEST VERSION: EO-BASED SCRAPER WITH FIXED PAGINATION'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f"Mode: {'Headless' if headless else 'Visible'}")

        if pages_per_eo:
            self.stdout.write(f"Safety limit: {pages_per_eo} pages per EO")
        else:
            self.stdout.write(f"No page limit - will scrape ALL available pages until pagination ends")

        if test_mode:
            self.stdout.write(self.style.WARNING("Test mode: Scraping only first 3 EO numbers"))

        # Initialize scraper
        scraper = CARBEOScraperTest(
            headless=headless,
            timeout=20,
            pages_per_eo=pages_per_eo
        )

        try:
            scraper._setup_driver()
            scraper.driver.get(scraper.BASE_URL)

            # Get EO numbers
            if eo_numbers_str:
                # Use specific EO numbers provided
                eo_numbers = [eo.strip() for eo in eo_numbers_str.split(',')]
                self.stdout.write(f"Scraping specific EO numbers: {eo_numbers}")
            else:
                # Extract all EO numbers from website
                eo_numbers = scraper.extract_eo_numbers()

                if test_mode and len(eo_numbers) > 3:
                    eo_numbers = eo_numbers[:3]
                    self.stdout.write(f"Limited to first 3 EO numbers for testing: {eo_numbers}")

            # Run the scraper
            stats = scraper.scrape_by_eo_numbers(eo_numbers)

            # Display results
            self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
            self.stdout.write(self.style.SUCCESS('SCRAPING COMPLETE'))
            self.stdout.write(self.style.SUCCESS('=' * 60))
            self.stdout.write(f"Total EOs processed: {stats['total_eos']}")
            self.stdout.write(f"Successful: {stats['successful_eos']}")
            self.stdout.write(f"Failed: {stats['failed_eos']}")
            self.stdout.write(f"Total converters found: {stats['total_converters']}")
            self.stdout.write(self.style.SUCCESS(f"Created: {stats['created']}"))
            self.stdout.write(self.style.SUCCESS(f"Updated: {stats['updated']}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            traceback.print_exc()
        finally:
            scraper._close_driver()
