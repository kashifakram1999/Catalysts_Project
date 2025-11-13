#!/usr/bin/env python3
"""
Test the complete website scraping flow
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def test_complete_scraping_flow():
    """Test scraping Honda with a specific year"""

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        print(f"Loading: {url}\n")
        driver.get(url)
        time.sleep(3)

        # STEP 1: Select Make (Honda)
        print("="*60)
        print("STEP 1: Select Make = Honda")
        print("="*60)

        make_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes"))
        )
        make_button.click()
        time.sleep(1)

        honda_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes') and text()='Honda']"
        honda_link = driver.find_element(By.XPATH, honda_xpath)
        honda_link.click()
        print("✓ Selected Honda")

        # STEP 2: Select Model Year
        print("\n" + "="*60)
        print("STEP 2: Select Model Year = 2015")
        print("="*60)

        # Wait for year button to exist, then use JavaScript to click (bypasses overlap issues)
        print("⏳ Waiting for Model Year button to be ready...")
        time.sleep(5)  # Give page time to fully load
        year_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModelYears")
        # Use JavaScript click to bypass loading panel overlay
        driver.execute_script("arguments[0].click();", year_button)
        print("✓ Clicked Model Year button")
        time.sleep(1)

        # Click on 2015 using JavaScript
        year_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModelYears') and text()='2015']"
        year_link = driver.find_element(By.XPATH, year_xpath)
        driver.execute_script("arguments[0].click();", year_link)
        print("✓ Selected 2015")

        # STEP 3: Select Model (Civic)
        print("\n" + "="*60)
        print("STEP 3: Select Model = Civic")
        print("="*60)

        print("⏳ Waiting for Model button to be ready...")
        time.sleep(5)  # Wait for models to load
        model_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModels")
        driver.execute_script("arguments[0].click();", model_button)
        print("✓ Clicked Model button")
        time.sleep(1)

        # Click on Civic
        model_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModels') and text()='Civic']"
        model_link = driver.find_element(By.XPATH, model_xpath)
        driver.execute_script("arguments[0].click();", model_link)
        print("✓ Selected Civic")

        # STEP 4: Click Search Button
        print("\n" + "="*60)
        print("STEP 4: Click Search Button")
        print("="*60)

        # Wait for search button, then use JavaScript click
        print("⏳ Waiting for Search button to be ready...")
        time.sleep(5)  # Give time for page to update
        search_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnVehicleSearch")
        driver.execute_script("arguments[0].click();", search_button)
        print("✓ Clicked Search")

        print("⏳ Waiting for results to load...")
        time.sleep(15)  # Wait longer for AJAX results to populate

        # Try scrolling down in case results are below viewport
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        # STEP 5: Analyze Results
        print("\n" + "="*60)
        print("STEP 5: Analyze Results")
        print("="*60)

        # Save results page
        with open('search_results.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot('search_results.png')
        print("✓ Saved search_results.html and search_results.png")

        # Look for tables
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nTables found: {len(tables)}")

        # Look for EO numbers in text
        body_text = driver.find_element(By.TAG_NAME, "body").text
        eo_matches = re.findall(r'D-\d+-\d+', body_text)
        print(f"Executive Orders found: {len(eo_matches)}")
        if eo_matches:
            print(f"Sample EOs: {eo_matches[:5]}")

        # Look for any data grids or repeaters
        data_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'result') or contains(@class, 'data') or contains(@class, 'grid')]")
        print(f"Data elements found: {len(data_elements)}")

        # Check for table rows with data
        all_rows = driver.find_elements(By.TAG_NAME, "tr")
        print(f"Total rows: {len(all_rows)}")

        if all_rows:
            print("\nSample rows:")
            for idx, row in enumerate(all_rows[:10]):
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells and len(cells) > 1:
                    row_data = [cell.text.strip()[:50] for cell in cells]
                    if any(row_data):  # Only show non-empty rows
                        print(f"  Row {idx+1} ({len(cells)} cells): {row_data}")

        # Look for manufacturer/company info
        print("\n" + "="*60)
        print("STEP 6: Look for Company/Converter Info")
        print("="*60)

        # Search for specific patterns
        if "Manufacturer" in body_text or "Company" in body_text:
            print("✓ Found manufacturer/company references")

        if "Civic" in body_text or "Accord" in body_text:
            print("✓ Found Honda model names")

        # Check for result count
        count_patterns = [r'(\d+)\s+results?', r'showing\s+(\d+)', r'found\s+(\d+)']
        for pattern in count_patterns:
            match = re.search(pattern, body_text, re.IGNORECASE)
            if match:
                print(f"✓ Found result count: {match.group(1)}")
                break

        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print("\nReview search_results.html and search_results.png")

        input("\nPress Enter to close...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        # Save error state
        try:
            driver.save_screenshot('error_screenshot.png')
            with open('error_page.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("\n✓ Saved error_screenshot.png and error_page.html")
        except:
            pass

    finally:
        driver.quit()


if __name__ == "__main__":
    test_complete_scraping_flow()
