#!/usr/bin/env python3
"""
Test what happens after EO search
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def test_eo_search_result():
    """Test the EO search and check result table"""

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

        # Click EO Search tab
        print("Clicking EO Search tab...")
        eo_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
        )
        driver.execute_script("arguments[0].click();", eo_tab)
        time.sleep(3)
        print("✓ Clicked EO Search tab")

        # Click EO dropdown
        print("\nOpening EO dropdown...")
        eo_dropdown = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers")
        driver.execute_script("arguments[0].click();", eo_dropdown)
        time.sleep(2)
        print("✓ Opened dropdown")

        # Click first EO (D-182-37)
        print("\nSelecting D-182-37...")
        eo_link = driver.find_element(
            By.XPATH,
            "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') and contains(text(), 'D-182-37')]"
        )

        # Use postback method
        href = eo_link.get_attribute('href')
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            target = match.group(1)
            argument = match.group(2)
            driver.execute_script(f"""
                var theForm = document.forms[0];
                theForm.__EVENTTARGET.value = '{target}';
                theForm.__EVENTARGUMENT.value = '{argument}';
                theForm.submit();
            """)
            print("✓ Triggered postback for D-182-37")

        time.sleep(10)  # Wait for results

        # Save page
        with open('eo_search_result.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        driver.save_screenshot('eo_search_result.png')
        print("\n✓ Saved eo_search_result.html and eo_search_result.png")

        # Look for result tables
        print("\nLooking for result tables...")
        tables = driver.find_elements(By.TAG_NAME, "table")
        print(f"Found {len(tables)} tables total")

        for i, table in enumerate(tables[:5], 1):
            table_id = table.get_attribute("id") or "no-id"
            table_class = table.get_attribute("class") or "no-class"
            print(f"  Table {i}: id={table_id}, class={table_class}")

        # Check for specific table IDs
        possible_ids = [
            "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData",
            "gvEOData",
            "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvARBEONumbers"
        ]

        print("\nChecking possible table IDs:")
        for table_id in possible_ids:
            try:
                table = driver.find_element(By.ID, table_id)
                print(f"  ✓ Found table: {table_id}")
                rows = table.find_elements(By.XPATH, ".//tr[td]")
                print(f"    - Has {len(rows)} data rows")
            except:
                print(f"  ✗ Not found: {table_id}")

        # Look for any EO numbers in page
        body_text = driver.find_element(By.TAG_NAME, "body").text
        eo_matches = re.findall(r'D-\d+-\d+', body_text)
        if eo_matches:
            print(f"\n✓ Found {len(eo_matches)} EO numbers in page")
            print(f"  Sample: {eo_matches[:5]}")

        input("\nPress Enter to close...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        try:
            driver.save_screenshot('eo_search_error.png')
            with open('eo_search_error.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
        except:
            pass

    finally:
        driver.quit()


if __name__ == "__main__":
    test_eo_search_result()
