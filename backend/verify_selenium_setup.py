#!/usr/bin/env python3
"""
Verify Selenium and ChromeDriver setup for website scraping
"""

import sys


def check_selenium():
    """Check if Selenium is installed"""
    try:
        import selenium
        print(f"✓ Selenium is installed (version {selenium.__version__})")
        return True
    except ImportError:
        print("✗ Selenium is NOT installed")
        print("  Install with: pip install selenium")
        return False


def check_chromedriver():
    """Check if ChromeDriver is accessible"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')

        # Try to create a driver
        driver = webdriver.Chrome(options=options)
        driver.quit()

        print("✓ ChromeDriver is working correctly")
        return True

    except Exception as e:
        print("✗ ChromeDriver is NOT working")
        print(f"  Error: {e}")
        print("\n  Installation instructions:")
        print("  - macOS: brew install chromedriver")
        print("  - Ubuntu/Debian: sudo apt-get install chromium-chromedriver")
        print("  - Manual: https://chromedriver.chromium.org/downloads")
        return False


def test_website_access():
    """Test if we can access the CARB website"""
    try:
        import requests

        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        response = requests.head(url, timeout=10)

        if response.status_code == 200:
            print("✓ CARB website is accessible")
            return True
        else:
            print(f"⚠ CARB website returned status code: {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Cannot access CARB website: {e}")
        return False


def main():
    print("=" * 60)
    print("Selenium Website Scraping Setup Verification")
    print("=" * 60)
    print()

    results = []

    # Check Selenium
    print("1. Checking Selenium installation...")
    results.append(check_selenium())
    print()

    # Check ChromeDriver
    print("2. Checking ChromeDriver...")
    results.append(check_chromedriver())
    print()

    # Check website access
    print("3. Checking CARB website access...")
    results.append(test_website_access())
    print()

    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)

    if all(results):
        print("✅ All checks passed! Website scraping is ready to use.")
        print("\nYou can now run:")
        print("  python manage.py scrape_website --test")
        sys.exit(0)
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nFor now, you can use PDF scraping:")
        print("  python manage.py scrape_carb_data")
        sys.exit(1)


if __name__ == "__main__":
    main()
