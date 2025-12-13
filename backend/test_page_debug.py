#!/usr/bin/env python3
"""
Debug script to see what's on the CARB website page
"""

import os
import sys
from playwright.sync_api import sync_playwright

def main():
    print("="*80)
    print("CARB WEBSITE DEBUG TEST")
    print("="*80)

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    # Get home directory for explicit executable path
    home = os.path.expanduser('~')
    executable_path = f"{home}/Library/Caches/ms-playwright/chromium_headless_shell-1200/chrome-headless-shell-mac-arm64/chrome-headless-shell"

    print(f"\nNavigating to: {BASE_URL}")
    print(f"Using browser: {executable_path}\n")

    playwright = None
    browser = None

    try:
        playwright = sync_playwright().start()

        # Launch browser
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=executable_path,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )

        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        print("Browser launched successfully")

        # Navigate to page
        print(f"Loading {BASE_URL}...")
        page.goto(BASE_URL, wait_until='networkidle', timeout=90000)
        print("✓ Page loaded")

        # Wait a bit
        import time
        time.sleep(5)

        # Get page title
        title = page.title()
        print(f"\nPage title: {title}")

        # Get page URL
        url = page.url
        print(f"Current URL: {url}")

        # Check for "EO Search" text
        print("\nSearching for 'EO Search' on page...")
        eo_search_elements = page.locator("text=EO Search").all()
        print(f"Found {len(eo_search_elements)} elements with 'EO Search' text")

        # Check for any links
        print("\nAll link texts on page:")
        links = page.locator("a").all()
        for i, link in enumerate(links[:20]):  # First 20 links
            try:
                text = link.inner_text(timeout=1000)
                if text.strip():
                    print(f"  {i+1}. {text.strip()}")
            except:
                pass

        # Check for tabs/navigation
        print("\nSearching for navigation/tabs...")
        nav_elements = page.locator("nav, .nav, .tabs, [role='tablist']").all()
        print(f"Found {len(nav_elements)} navigation elements")

        # Take a screenshot for debugging
        screenshot_path = "/Users/muhmmadkashif/Documents/GitHub/Catalysts_Project/backend/debug_screenshot.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"\n✓ Screenshot saved to: {screenshot_path}")

        # Get page HTML snippet
        print("\nPage body snippet (first 500 chars):")
        body_text = page.locator("body").inner_text()
        print(body_text[:500])

        print("\n" + "="*80)
        print("DEBUG TEST COMPLETE")
        print("="*80)

        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        if browser:
            browser.close()
        if playwright:
            playwright.stop()

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
