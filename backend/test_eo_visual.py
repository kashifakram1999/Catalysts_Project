#!/usr/bin/env python3
"""
Visual test of EO scraper to see what's happening
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def test_eo_visual():
    """Test EO scraper with visible browser"""

    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    # VISIBLE BROWSER - no headless

    driver = webdriver.Chrome(options=options)

    try:
        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        print(f"Step 1: Loading {url}")
        driver.get(url)
        time.sleep(3)
        print("✓ Page loaded\n")

        # STEP 1: Click EO Search tab
        print("Step 2: Clicking EO Search tab...")
        eo_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
        )
        driver.execute_script("arguments[0].click();", eo_tab)
        time.sleep(3)
        print("✓ EO Search tab clicked\n")

        # STEP 2: Click EO dropdown button
        print("Step 3: Clicking EO dropdown button (btnARBEONumbers)...")
        eo_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"))
        )
        # Scroll into view first
        driver.execute_script("arguments[0].scrollIntoView(true);", eo_dropdown)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", eo_dropdown)
        time.sleep(2)
        print("✓ EO dropdown clicked\n")

        # STEP 3: Click first EO (D-182-37)
        print("Step 4: Selecting EO number D-182-37...")
        eo_xpath = "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') and contains(text(), 'D-182-37')]"
        eo_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, eo_xpath))
        )

        # Extract postback and trigger it
        href = eo_link.get_attribute('href')
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            target = match.group(1)
            argument = match.group(2)
            print(f"  Found postback: target={target}, argument={argument}")
            driver.execute_script(f"""
                var theForm = document.forms[0];
                theForm.__EVENTTARGET.value = '{target}';
                theForm.__EVENTARGUMENT.value = '{argument}';
                theForm.submit();
            """)
            print("✓ Triggered postback for D-182-37\n")
        else:
            driver.execute_script("arguments[0].click();", eo_link)
            print("✓ Clicked D-182-37 (fallback)\n")

        # Wait for page to update
        print("Step 5: Waiting for page to update after EO selection...")
        time.sleep(5)
        print("✓ Page should have updated\n")

        # STEP 4: Check if we're still on EO Search tab
        print("Step 6: Verifying we're on EO Search tab...")
        try:
            # Check if EO Search tab is active
            active_tab = driver.find_element(By.CSS_SELECTOR, "li.active a")
            tab_text = active_tab.text
            print(f"  Active tab: {tab_text}")

            if "EO Search" not in tab_text:
                print("⚠ WARNING: Not on EO Search tab! Clicking it again...")
                eo_tab = driver.find_element(By.LINK_TEXT, "EO Search")
                driver.execute_script("arguments[0].click();", eo_tab)
                time.sleep(3)
        except:
            print("⚠ Could not determine active tab")

        # STEP 5: Find and click Search button
        print("\nStep 7: Looking for Search button (btnEOSearch)...")
        try:
            search_button = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnEOSearch"))
            )

            # Check if button is disabled
            button_class = search_button.get_attribute("class") or ""
            is_disabled = "disabled" in button_class or "aspNetDisabled" in button_class

            print(f"  Button found. Classes: {button_class}")
            print(f"  Is disabled: {is_disabled}")

            if is_disabled:
                print("⚠ WARNING: Search button is DISABLED!")
                print("  This means EO selection didn't work properly")
            else:
                print("✓ Search button is ENABLED")
                print("\nStep 8: Clicking Search button...")
                driver.execute_script("arguments[0].scrollIntoView(true);", search_button)
                time.sleep(1)
                driver.execute_script("arguments[0].click();", search_button)
                print("✓ Search button clicked\n")

                # Wait for results
                print("Step 9: Waiting for results...")
                time.sleep(10)

                # Check for results table
                try:
                    table = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")
                    rows = table.find_elements(By.XPATH, ".//tr[td]")
                    print(f"✓ Results table found with {len(rows)} data rows!\n")
                except:
                    print("✗ No results table found\n")

        except Exception as e:
            print(f"✗ Error finding/clicking search button: {e}\n")

        print("\n" + "="*60)
        print("TEST COMPLETE - Browser will stay open for 30 seconds")
        print("="*60)
        time.sleep(30)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        time.sleep(10)

    finally:
        driver.quit()


if __name__ == "__main__":
    test_eo_visual()
