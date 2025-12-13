#!/usr/bin/env python3
"""
Single-worker test script for Playwright scraper

This script tests scraping with a single worker to avoid SQLite
database locking issues that occur with parallel workers.

Usage:
    python test_single_eo.py
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
# Allow sync database operations in Playwright's sync context
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
django.setup()

from converters.eo_scraper_playwright import CARBPlaywrightScraper
from converters.models import ScraperRun

def main():
    print("="*80)
    print("PLAYWRIGHT SCRAPER - SINGLE WORKER TEST")
    print("="*80)
    print("\nThis test will scrape 3 EO numbers sequentially")
    print("(avoiding SQLite database locking issues)\n")

    # Test EO numbers
    test_eos = ['D-724-2', 'D-724-3', 'D-724-5']

    # Create scraper
    print("Initializing Playwright scraper...")
    scraper = CARBPlaywrightScraper(headless=True, timeout=20, pages_per_eo=5)  # Using headless mode

    try:
        # Create ScraperRun for tracking (browser will auto-initialize when scraping starts)
        print("Creating ScraperRun for tracking...")
        scraper_run = ScraperRun.objects.create(
            task_id='test-single-worker',
            scraper_type='single',
            headless=False,
            pages_per_eo=5,
            test_mode=True,
            eo_numbers_to_process=test_eos,
            total_eo_count=len(test_eos),
            engine_used='playwright',
        )
        print(f"✓ Created ScraperRun {scraper_run.id}\n")

        # Scrape EO numbers
        print("Starting scrape...")
        print("-"*80)
        stats = scraper.scrape_by_eo_numbers(
            test_eos,
            scraper_run_id=scraper_run.id
        )
        print("-"*80)

        # Display results
        print("\n" + "="*80)
        print("SCRAPING RESULTS")
        print("="*80)
        print(f"Total EOs: {stats['total_eo_count']}")
        print(f"✓ Success: {stats['success_count']}")
        print(f"✗ Failed: {stats['failed_count']}")
        print(f"∅ No Results: {stats['no_results_count']}")
        print(f"⚠ Partial: {stats['partial_count']}")
        print(f"📊 Converters Created: {stats['converters_created']}")
        print(f"📊 Converters Updated: {stats['converters_updated']}")

        # Display failure details if any
        if stats['eo_failure_details']:
            print("\n" + "="*80)
            print("FAILURE DETAILS (Zero Silent Failures!)")
            print("="*80)
            for eo_number, details in stats['eo_failure_details'].items():
                print(f"\n{eo_number}:")
                print(f"  Attempts: {details['attempts']}")
                print(f"  Error Type: {details['error_type']}")
                print(f"  Last Error: {details['last_error']}")
                print(f"  Failed at Page: {details['failed_at_page']}")
                print(f"  Timestamp: {details['timestamp']}")
                if details.get('retry_history'):
                    print(f"  Retry History:")
                    for attempt in details['retry_history']:
                        print(f"    - Attempt {attempt['attempt']}: {attempt['error_msg'][:50]}...")

        # Update ScraperRun with results
        scraper_run.success_count = stats['success_count']
        scraper_run.failed_count = stats['failed_count']
        scraper_run.no_results_count = stats['no_results_count']
        scraper_run.partial_count = stats['partial_count']
        scraper_run.processed_count = stats['success_count'] + stats['failed_count'] + stats['no_results_count'] + stats['partial_count']
        scraper_run.eo_failure_details = stats['eo_failure_details']
        scraper_run.eo_retry_queue = stats['retry_queue']
        scraper_run.status = 'completed'
        scraper_run.save()

        print("\n✓ ScraperRun updated in database")
        print(f"✓ View in admin: http://localhost:8000/admin/converters/scraperrun/{scraper_run.id}/")

        # Success summary
        success_rate = (stats['success_count'] / stats['total_eo_count'] * 100) if stats['total_eo_count'] > 0 else 0
        print(f"\n{'='*80}")
        print(f"SUCCESS RATE: {success_rate:.1f}%")
        print(f"{'='*80}")

        if stats['retry_queue']:
            print(f"\n⚠ {len(stats['retry_queue'])} EOs in retry queue: {stats['retry_queue']}")
            print("These can be retried automatically or manually")

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Clean up
        if scraper.browser:
            print("\nClosing browser...")
            scraper._close_driver()
            print("✓ Browser closed")
        else:
            print("\n✓ No browser to close")

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
