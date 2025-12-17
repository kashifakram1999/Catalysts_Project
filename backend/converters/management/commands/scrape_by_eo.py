"""
Django management command to scrape CARB data using EO number search
"""

from django.core.management.base import BaseCommand
from converters.eo_scraper import CARBEOScraper
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape CARB catalytic converter data by Executive Order numbers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--pages',
            type=int,
            default=None,
            help='Maximum pages to scrape per EO (default: unlimited - scrapes all available pages)'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=20,
            help='Timeout for element waits in seconds (default: 20)'
        )
        parser.add_argument(
            '--headless',
            action='store_true',
            default=True,
            help='Run browser in headless mode (default: True)'
        )
        parser.add_argument(
            '--visible',
            action='store_true',
            help='Run browser in visible mode (overrides --headless)'
        )
        parser.add_argument(
            '--test',
            action='store_true',
            help='Test mode: scrape only first 3 EO numbers'
        )
        parser.add_argument(
            '--eo-numbers',
            type=str,
            help='Comma-separated list of specific EO numbers to scrape (e.g., "D-393-143,D-393-144")'
        )
        parser.add_argument(
            '--scraper-run-id',
            type=int,
            default=None,
            help='ScraperRun ID for stop/resume tracking (optional)'
        )

    def handle(self, *args, **options):
        pages = options['pages']
        timeout = options['timeout']
        headless = not options['visible'] if options['visible'] else options['headless']
        test_mode = options['test']
        eo_numbers_arg = options['eo_numbers']
        scraper_run_id = options.get('scraper_run_id')

        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("CARB EO-Based Website Scraper"))
        self.stdout.write("=" * 70)
        if pages:
            self.stdout.write(f"Pages per EO: {pages} (safety limit)")
        else:
            self.stdout.write(f"Pages per EO: Unlimited (scrape all available pages)")
        self.stdout.write(f"Timeout: {timeout}s")
        self.stdout.write(f"Headless: {headless}")
        if test_mode:
            self.stdout.write(self.style.WARNING("TEST MODE: Will scrape only first 3 EO numbers"))
        if eo_numbers_arg:
            self.stdout.write(f"Specific EO numbers: {eo_numbers_arg}")
        self.stdout.write("")

        # Initialize scraper
        scraper = CARBEOScraper(
            headless=headless,
            timeout=timeout,
            pages_per_eo=pages
        )

        try:
            # Setup driver
            scraper._setup_driver()

            # Determine which EO numbers to scrape
            if eo_numbers_arg:
                # Use specific EO numbers from command line
                eo_numbers = [eo.strip() for eo in eo_numbers_arg.split(',')]
                self.stdout.write(f"Using {len(eo_numbers)} EO numbers from command line")
            else:
                # Extract EO numbers from website
                self.stdout.write("Extracting EO numbers from website dropdown...")
                eo_numbers = scraper.extract_eo_numbers()

                if not eo_numbers:
                    self.stdout.write(self.style.ERROR("Failed to extract EO numbers"))
                    return

                self.stdout.write(self.style.SUCCESS(f"Found {len(eo_numbers)} EO numbers"))

                # Apply test mode limit
                if test_mode:
                    eo_numbers = eo_numbers[:3]
                    self.stdout.write(self.style.WARNING(f"Test mode: limited to {len(eo_numbers)} EO numbers"))

            # Start scraping
            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write(f"Starting scrape for {len(eo_numbers)} EO numbers...")
            self.stdout.write("=" * 70)
            self.stdout.write("")

            stats = scraper.scrape_by_eo_numbers(eo_numbers, scraper_run_id=scraper_run_id)

            # Display results
            self.stdout.write("")
            self.stdout.write("=" * 70)
            self.stdout.write(self.style.SUCCESS("SCRAPING COMPLETE"))
            self.stdout.write("=" * 70)
            self.stdout.write(f"Total EOs processed: {stats['total_eos']}")
            self.stdout.write(f"Successful: {stats['successful_eos']}")
            self.stdout.write(f"Failed: {stats['failed_eos']}")
            self.stdout.write(f"Total converters found: {stats['total_converters']}")
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"✓ Created: {stats['created']} new records"))
            self.stdout.write(self.style.SUCCESS(f"✓ Updated: {stats['updated']} existing records"))
            self.stdout.write("")

            # Calculate coverage percentage
            if stats['total_eos'] > 0:
                success_rate = (stats['successful_eos'] / stats['total_eos']) * 100
                self.stdout.write(f"Success rate: {success_rate:.1f}%")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during scraping: {e}"))
            import traceback
            traceback.print_exc()
        finally:
            scraper._close_driver()
