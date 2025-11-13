#!/usr/bin/env python3
"""
Quick test of Honda scraping using the website scraper
"""
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.website_scraper import CARBWebsiteScraper

def test_honda():
    """Test scraping Honda specifically"""
    print("Testing Honda scraping...\n")

    scraper = CARBWebsiteScraper(headless=True, timeout=30)

    try:
        scraper._setup_driver()
        scraper.driver.get("https://ssl.arb.ca.gov/AftermarketParts/catalysts")
        print("Loaded website\n")

        # Scrape Honda
        print("Scraping Honda...")
        results = scraper._scrape_manufacturer("Honda")

        print(f"\n{'='*60}")
        print(f"Results: {len(results)} converters found")
        print(f"{'='*60}")

        if results:
            print("\nSample converter data:")
            for i, converter in enumerate(results[:3], 1):
                print(f"\n  Converter {i}:")
                for key, value in converter.items():
                    if key != 'scraped_at':
                        print(f"    {key}: {value}")
        else:
            print("\n⚠ No converters found")

    finally:
        scraper._close_driver()

if __name__ == "__main__":
    test_honda()
