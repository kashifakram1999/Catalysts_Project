#!/usr/bin/env python3
"""
Test script to verify CARB website scraping capability
"""

import requests
from bs4 import BeautifulSoup


def test_base_url_access():
    """Test if we can access the base URL"""
    url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    print("=" * 60)
    print("Testing CARB Base URL Access")
    print("=" * 60)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        print(f"\n1. Attempting to fetch: {url}")
        response = requests.get(url, headers=headers, timeout=10)

        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response.elapsed.total_seconds():.2f}s")

        if response.status_code == 200:
            print("   ✓ Successfully accessed the website")

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Check for ASP.NET indicators
            print("\n2. Analyzing page structure:")
            viewstate = soup.find('input', {'id': '__VIEWSTATE'})
            if viewstate:
                print("   ✓ Found ASP.NET ViewState (complex scraping required)")

            # Check for forms
            forms = soup.find_all('form')
            print(f"   ✓ Found {len(forms)} form(s)")

            # Check for dropdowns
            selects = soup.find_all('select')
            print(f"   ✓ Found {len(selects)} dropdown(s)")

            # Check for manufacturer list
            make_options = soup.find_all('option')
            manufacturers = [opt.text.strip() for opt in make_options if opt.text.strip() and opt.text.strip() != 'Select']
            if manufacturers:
                print(f"   ✓ Found {len(manufacturers)} manufacturer options")
                print(f"   Examples: {', '.join(manufacturers[:5])}")

            print("\n3. Scraping Complexity Assessment:")
            print("   ⚠ This is an ASP.NET site with AJAX")
            print("   ⚠ Requires Selenium for proper scraping")
            print("   ⚠ Simple requests won't retrieve dynamic data")
            print("   ✓ Website is accessible (no blocking)")

            return True
        else:
            print(f"   ✗ Failed to access website: HTTP {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error: {e}")
        return False


def test_pdf_url_access():
    """Test if we can access the PDF URL"""
    url = "https://ww2.arb.ca.gov/sites/default/files/aftermarket/aftermktcat/exemptcat09.pdf"

    print("\n" + "=" * 60)
    print("Testing CARB PDF URL Access")
    print("=" * 60)

    try:
        print(f"\n1. Attempting to fetch: {url}")
        response = requests.head(url, timeout=10)

        print(f"   Status Code: {response.status_code}")

        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            content_length = response.headers.get('Content-Length', 'Unknown')

            print(f"   Content-Type: {content_type}")
            print(f"   Content-Length: {int(content_length) / 1024:.2f} KB" if content_length != 'Unknown' else "   Content-Length: Unknown")
            print("   ✓ PDF is accessible and can be downloaded")
            print("\n   Recommendation: PDF scraping is MUCH easier than website scraping")
            return True
        else:
            print(f"   ✗ Failed to access PDF: HTTP {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"   ✗ Error: {e}")
        return False


def main():
    print("\n🔍 CARB Data Source Verification\n")

    # Test both URLs
    website_ok = test_base_url_access()
    pdf_ok = test_pdf_url_access()

    print("\n" + "=" * 60)
    print("Summary & Recommendations")
    print("=" * 60)

    if pdf_ok:
        print("\n✓ RECOMMENDED: Use PDF scraping (currently implemented)")
        print("  - Faster and more reliable")
        print("  - Contains all historical data")
        print("  - No complex browser automation needed")
        print("  - Already working in your project")

    if website_ok:
        print("\n⚠ ALTERNATIVE: Website scraping (requires Selenium)")
        print("  - More complex implementation")
        print("  - Slower due to browser automation")
        print("  - May have up-to-date data")
        print("  - Currently only partially implemented")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
