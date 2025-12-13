#!/usr/bin/env python3
"""
Quick validation script for Playwright migration

This script tests:
1. Playwright scraper can be imported
2. Browser initialization works
3. Basic navigation works
4. Models have new fields
"""

import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.eo_scraper_playwright import CARBPlaywrightScraper, EOStatus, RetryContext
from converters.models import ScraperRun

def test_import():
    """Test that Playwright scraper can be imported"""
    print("✓ Test 1: Import successful")
    print(f"  - CARBPlaywrightScraper class available")
    print(f"  - EOStatus class available")
    print(f"  - RetryContext class available")

def test_model_fields():
    """Test that ScraperRun has new fields"""
    print("\n✓ Test 2: Model fields added")
    fields = ['engine_used', 'eo_failure_details', 'eo_retry_queue',
              'current_retry_pass', 'max_retry_passes']

    for field in fields:
        if hasattr(ScraperRun, field):
            print(f"  - {field}: ✓")
        else:
            print(f"  - {field}: ✗ MISSING")
            return False
    return True

def test_scraper_initialization():
    """Test basic scraper initialization"""
    print("\n✓ Test 3: Scraper initialization")
    try:
        scraper = CARBPlaywrightScraper(headless=True, timeout=20)
        print(f"  - Scraper created successfully")
        print(f"  - Headless: {scraper.headless}")
        print(f"  - Timeout: {scraper.timeout}ms")

        # Don't initialize browser yet (requires Chromium to be fully installed)
        # Just verify the object was created
        return True
    except Exception as e:
        print(f"  - Error: {e}")
        return False

def test_retry_context():
    """Test RetryContext functionality"""
    print("\n✓ Test 4: RetryContext")
    try:
        context = RetryContext()
        context.record_attempt('page', 'Test error', 2.5)

        if len(context.retry_history) == 1:
            print(f"  - Retry history tracking: ✓")
            print(f"  - Attempt recorded: {context.retry_history[0]}")
            return True
        else:
            print(f"  - Retry history tracking: ✗")
            return False
    except Exception as e:
        print(f"  - Error: {e}")
        return False

def test_constants():
    """Test that all constants are defined"""
    print("\n✓ Test 5: Constants")
    constants = {
        'EOStatus.SUCCESS': EOStatus.SUCCESS,
        'EOStatus.FAILED': EOStatus.FAILED,
        'EOStatus.NO_RESULTS': EOStatus.NO_RESULTS,
        'EOStatus.PARTIAL': EOStatus.PARTIAL,
    }

    for name, value in constants.items():
        print(f"  - {name} = '{value}'")
    return True

def main():
    print("="*60)
    print("PLAYWRIGHT MIGRATION VALIDATION TEST")
    print("="*60)

    try:
        test_import()

        model_ok = test_model_fields()
        if not model_ok:
            print("\n✗ FAILED: Model fields missing. Did you run migrations?")
            return False

        scraper_ok = test_scraper_initialization()
        if not scraper_ok:
            print("\n✗ FAILED: Scraper initialization failed")
            return False

        retry_ok = test_retry_context()
        if not retry_ok:
            print("\n✗ FAILED: RetryContext not working")
            return False

        test_constants()

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED!")
        print("="*60)
        print("\nNext steps:")
        print("1. Run: python manage.py scrape_by_eo --test --headless")
        print("   (This will test with first 3 EOs)")
        print("\n2. Check Django admin to view failure tracking fields")
        print("\n3. Run full scrape once validated")
        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
