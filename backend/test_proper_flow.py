#!/usr/bin/env python3
"""
Test the PROPER website scraping flow as described by user
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def test_proper_flow():
    """Test scraping following the exact field enabling sequence"""

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

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

        make_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes")
        driver.execute_script("arguments[0].click();", make_button)
        time.sleep(1)

        # Get the postback target from Honda link
        honda_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes') and text()='Honda']"
        honda_link = driver.find_element(By.XPATH, honda_xpath)

        # Extract the postback arguments and set form fields directly
        href = honda_link.get_attribute('href')
        # Extract the postback parameters from javascript:__doPostBack('target','argument')
        import re
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            target = match.group(1)
            argument = match.group(2)
            # Set hidden fields and submit form (bypasses strict mode issues)
            driver.execute_script(f"""
                var theForm = document.forms[0];
                theForm.__EVENTTARGET.value = '{target}';
                theForm.__EVENTARGUMENT.value = '{argument}';
                theForm.submit();
            """)
            print(f"✓ Triggered postback for Honda")
        else:
            driver.execute_script("arguments[0].click();", honda_link)
            print("✓ Clicked Honda (fallback)")

        print("⏳ Waiting for page to update and Model Year field to enable...")
        time.sleep(8)  # Wait longer for ASP.NET postback

        # STEP 2: Select Model Year (2015)
        print("\n" + "="*60)
        print("STEP 2: Select Model Year = 2015")
        print("="*60)

        year_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModelYears")
        driver.execute_script("arguments[0].click();", year_button)
        time.sleep(1)

        year_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModelYears') and text()='2015']"
        year_link = driver.find_element(By.XPATH, year_xpath)

        # Use postback for Year selection
        href = year_link.get_attribute('href')
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            target = match.group(1)
            argument = match.group(2)
            # Set hidden fields and submit form (bypasses strict mode issues)
            driver.execute_script(f"""
                var theForm = document.forms[0];
                theForm.__EVENTTARGET.value = '{target}';
                theForm.__EVENTARGUMENT.value = '{argument}';
                theForm.submit();
            """)
            print(f"✓ Triggered postback for 2015")
        else:
            driver.execute_script("arguments[0].click();", year_link)
            print("✓ Clicked 2015 (fallback)")

        print("⏳ Waiting for page to update and Model field to enable...")
        time.sleep(8)

        # STEP 3: Select Model (Civic)
        print("\n" + "="*60)
        print("STEP 3: Select Model = Civic")
        print("="*60)

        model_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModels")
        driver.execute_script("arguments[0].click();", model_button)
        time.sleep(1)

        model_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModels') and text()='Civic']"
        model_link = driver.find_element(By.XPATH, model_xpath)
        driver.execute_script("arguments[0].click();", model_link)
        print("✓ Selected Civic")
        print("⏳ Waiting for Engine Size field to enable...")
        time.sleep(5)

        # STEP 4: Check if Engine Size is required or if Search is already enabled
        print("\n" + "="*60)
        print("STEP 4: Check Engine Size / Search Button Status")
        print("="*60)

        # Check if search button is enabled
        search_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnVehicleSearch")
        is_disabled = "disabled" in search_button.get_attribute("class")

        if is_disabled:
            print("⚠ Search button still disabled, need to select Engine Size")

            # Select first available engine size
            engine_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnEngineSizes")
            driver.execute_script("arguments[0].click();", engine_button)
            time.sleep(1)

            # Get first available engine size option
            engine_links = driver.find_elements(
                By.XPATH,
                "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrEngineSizes')]"
            )

            if engine_links:
                first_engine = engine_links[0]
                engine_text = first_engine.text.strip()
                driver.execute_script("arguments[0].click();", first_engine)
                print(f"✓ Selected Engine Size: {engine_text}")
                print("⏳ Waiting for Search button to enable...")
                time.sleep(5)
            else:
                print("✗ No engine size options found")
        else:
            print("✓ Search button is already enabled (Engine Size optional)")

        # STEP 5: Click Search Button
        print("\n" + "="*60)
        print("STEP 5: Click Search Button")
        print("="*60)

        search_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnVehicleSearch")
        driver.execute_script("arguments[0].click();", search_button)
        print("✓ Clicked Search")

        print("⏳ Waiting for results to load (15 seconds)...")
        time.sleep(15)

        # STEP 6: Analyze Results
        print("\n" + "="*60)
        print("STEP 6: Analyze Results")
        print("="*60)

        # Save results
        with open('final_results.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot('final_results.png')
        print("✓ Saved final_results.html and final_results.png")

        # Look for result indicators
        body_text = driver.find_element(By.TAG_NAME, "body").text

        # Check for tables with data
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"\nTables found: {len(tables)}")

        # Check for rows
        all_rows = driver.find_elements(By.TAG_NAME, "tr")
        data_rows = [row for row in all_rows if row.find_elements(By.TAG_NAME, "td")]
        print(f"Data rows found: {len(data_rows)}")

        if data_rows:
            print("\nSample data rows:")
            for idx, row in enumerate(data_rows[:5]):
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = [cell.text.strip()[:40] for cell in cells]
                print(f"  Row {idx+1}: {row_data}")

        # Look for EO numbers
        eo_matches = re.findall(r'D-\d+-\d+', body_text)
        if eo_matches:
            print(f"\n✓ Found {len(eo_matches)} Executive Orders:")
            print(f"  Sample: {eo_matches[:10]}")
        else:
            print("\n✗ No Executive Orders found in results")

        # Look for company names
        if "Company" in body_text or "Manufacturer" in body_text:
            print("✓ Found manufacturer/company information")

        # Check results section
        results_section = driver.find_elements(By.CLASS_NAME, "search-results")
        if results_section:
            results_html = results_section[0].get_attribute('innerHTML')
            if results_html.strip():
                print(f"✓ Results section has content ({len(results_html)} characters)")
            else:
                print("⚠ Results section exists but is empty")

        print("\n" + "="*60)
        print("TESTING COMPLETE")
        print("="*60)
        print("\nReview final_results.html and final_results.png for details")

        input("\nPress Enter to close...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        try:
            driver.save_screenshot('error_final.png')
            with open('error_final.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("\n✓ Saved error_final.png and error_final.html")
        except:
            pass

    finally:
        driver.quit()


if __name__ == "__main__":
    test_proper_flow()
