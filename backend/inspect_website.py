#!/usr/bin/env python3
"""
Inspect the CARB website structure to understand how to scrape it
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def inspect_website():
    """Inspect the website structure"""

    options = webdriver.ChromeOptions()
    # Run visible to see what's happening
    # options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        print(f"Loading: {url}")
        driver.get(url)

        # Wait for page to load
        time.sleep(5)

        print("\n" + "="*60)
        print("PAGE STRUCTURE ANALYSIS")
        print("="*60)

        # 1. Check page title
        print(f"\n1. Page Title: {driver.title}")

        # 2. Look for forms
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"\n2. Found {len(forms)} form(s)")

        # 3. Look for tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\n3. Found {len(tables)} table(s)")

        # 4. Look for divs with specific classes or IDs
        print("\n4. Main DIV elements:")
        main_divs = driver.find_elements(By.XPATH, "//div[@id or @class]")[:10]
        for div in main_divs:
            div_id = div.get_attribute('id')
            div_class = div.get_attribute('class')
            if div_id or div_class:
                print(f"   - ID: {div_id or 'None'}, Class: {div_class or 'None'}")

        # 5. Look for links
        links = driver.find_elements(By.TAG_NAME, "a")
        print(f"\n5. Found {len(links)} link(s)")
        print("   First 10 links:")
        for link in links[:10]:
            text = link.text.strip()
            href = link.get_attribute('href')
            if text:
                print(f"   - {text[:50]} -> {href[:50] if href else 'No href'}...")

        # 6. Look for select/dropdowns
        selects = driver.find_elements(By.TAG_NAME, "select")
        print(f"\n6. Found {len(selects)} dropdown(s)")
        for idx, select in enumerate(selects):
            select_id = select.get_attribute('id')
            select_name = select.get_attribute('name')
            options = select.find_elements(By.TAG_NAME, "option")
            print(f"   Dropdown {idx+1}: ID={select_id}, Name={select_name}, Options={len(options)}")
            if options:
                print(f"      First 5 options: {[opt.text.strip() for opt in options[:5]]}")

        # 7. Look for input fields
        inputs = driver.find_elements(By.TAG_NAME, "input")
        print(f"\n7. Found {len(inputs)} input field(s)")
        visible_inputs = [inp for inp in inputs if inp.is_displayed()]
        print(f"   Visible inputs: {len(visible_inputs)}")

        # 8. Look for any data that looks like manufacturers
        print("\n8. Looking for manufacturer-like data...")
        # Try to find any element with text that looks like a manufacturer
        all_text = driver.find_element(By.TAG_NAME, "body").text
        if "Honda" in all_text or "Toyota" in all_text or "Ford" in all_text:
            print("   ✓ Found manufacturer names in page text")
        else:
            print("   ✗ No obvious manufacturer names found")

        # 9. Check for ASP.NET specific elements
        print("\n9. ASP.NET Elements:")
        viewstate = driver.find_elements(By.ID, "__VIEWSTATE")
        print(f"   __VIEWSTATE: {'Found' if viewstate else 'Not found'}")

        eventvalidation = driver.find_elements(By.ID, "__EVENTVALIDATION")
        print(f"   __EVENTVALIDATION: {'Found' if eventvalidation else 'Not found'}")

        # 10. Save page source for manual inspection
        print("\n10. Saving page source to 'page_source.html'...")
        with open('page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("   ✓ Saved to page_source.html")

        # 11. Take screenshot
        print("\n11. Taking screenshot...")
        driver.save_screenshot('website_screenshot.png')
        print("   ✓ Saved to website_screenshot.png")

        print("\n" + "="*60)
        print("INSPECTION COMPLETE")
        print("="*60)
        print("\nNext steps:")
        print("1. Review page_source.html to understand structure")
        print("2. Check website_screenshot.png to see visual layout")
        print("3. Update scraper based on actual structure")

        # Keep browser open for manual inspection
        input("\nPress Enter to close browser...")

    finally:
        driver.quit()


if __name__ == "__main__":
    inspect_website()
