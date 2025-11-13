#!/usr/bin/env python3
"""
Debug the complete website flow to understand data structure
This will help us build the proper scraper
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

def debug_website_flow():
    """Step through the website flow to understand structure"""

    options = webdriver.ChromeOptions()
    # Run visible to see what's happening
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        print(f"Loading: {url}")
        driver.get(url)
        time.sleep(3)

        print("\n" + "="*60)
        print("STEP 1: Click Make Dropdown")
        print("="*60)

        # Click Make dropdown
        make_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes"))
        )
        print("✓ Found Make button")
        make_button.click()
        time.sleep(1)

        # Get all manufacturers
        make_links = driver.find_elements(
            By.XPATH,
            "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes')]"
        )
        print(f"✓ Found {len(make_links)} manufacturers")

        # Test with Honda (common manufacturer)
        test_manufacturer = "Honda"
        print(f"\n{'='*60}")
        print(f"STEP 2: Click on {test_manufacturer}")
        print("="*60)

        # Find and click Honda
        honda_xpath = f"//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes') and text()='{test_manufacturer}']"
        honda_link = driver.find_element(By.XPATH, honda_xpath)
        print(f"✓ Found {test_manufacturer} link")
        honda_link.click()

        print("⏳ Waiting for results to load...")
        time.sleep(5)  # Give AJAX time to complete

        print("\n" + "="*60)
        print("STEP 3: Analyze Results Structure")
        print("="*60)

        # Check for any tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nTables found: {len(tables)}")

        # Check for divs that might contain results
        result_divs = driver.find_elements(By.XPATH, "//div[contains(@class, 'result') or contains(@class, 'data') or contains(@class, 'grid')]")
        print(f"Result divs found: {len(result_divs)}")

        # Check for any list elements
        lists = driver.find_elements(By.TAG_NAME, "ul")
        print(f"Lists found: {len(lists)}")

        # Look for any panels or cards
        panels = driver.find_elements(By.XPATH, "//div[contains(@class, 'panel') or contains(@class, 'card')]")
        print(f"Panels/cards found: {len(panels)}")

        # Check for Telerik RadGrid (common ASP.NET control)
        radgrids = driver.find_elements(By.XPATH, "//div[contains(@class, 'RadGrid')]")
        print(f"RadGrids found: {len(radgrids)}")

        # Save current page source
        print("\n" + "="*60)
        print("STEP 4: Save Results Page")
        print("="*60)

        with open('results_page_source.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("✓ Saved to results_page_source.html")

        driver.save_screenshot('results_screenshot.png')
        print("✓ Saved to results_screenshot.png")

        # Try to find any visible text with converter info
        print("\n" + "="*60)
        print("STEP 5: Look for Converter Data")
        print("="*60)

        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Look for EO patterns (D-###-##)
        import re
        eo_matches = re.findall(r'D-\d+-\d+', body_text)
        print(f"\nExecutive Orders found in text: {len(eo_matches)}")
        if eo_matches:
            print(f"First 5 EOs: {eo_matches[:5]}")

        # Look for year patterns
        year_matches = re.findall(r'\b(19|20)\d{2}\b', body_text)
        print(f"Years found in text: {len(set(year_matches))}")

        # Check for pagination
        print("\n" + "="*60)
        print("STEP 6: Check for Pagination")
        print("="*60)

        pagination = driver.find_elements(By.XPATH, "//div[contains(@class, 'pag') or contains(@class, 'page')]")
        print(f"Pagination elements found: {len(pagination)}")

        # Look for "next" or "more" buttons
        next_buttons = driver.find_elements(By.XPATH, "//a[contains(text(), 'Next') or contains(text(), 'More') or contains(text(), '>')]")
        print(f"Next/More buttons found: {len(next_buttons)}")

        print("\n" + "="*60)
        print("STEP 7: Extract Sample Data")
        print("="*60)

        # Try to find actual data rows
        # Look for repeating structures that might contain converter data

        # Check all table rows
        all_rows = driver.find_elements(By.TAG_NAME, "tr")
        print(f"\nTotal <tr> elements: {len(all_rows)}")

        if all_rows:
            print("\nAnalyzing first few rows:")
            for idx, row in enumerate(all_rows[:5]):
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    row_text = [cell.text.strip() for cell in cells]
                    print(f"  Row {idx+1}: {len(cells)} cells - {row_text}")

        # Check for any div-based data structures
        data_rows = driver.find_elements(By.XPATH, "//div[contains(@class, 'row') and not(contains(@class, 'container'))]")
        print(f"\nDiv-based rows: {len(data_rows)}")

        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print("\nFiles created:")
        print("  - results_page_source.html (inspect HTML structure)")
        print("  - results_screenshot.png (visual reference)")
        print("\nNext: Review these files to understand data structure")

        input("\nPress Enter to close browser and continue...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()


if __name__ == "__main__":
    debug_website_flow()
