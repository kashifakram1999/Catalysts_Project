#!/usr/bin/env python3
"""
Test EO scraper flow
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def test_eo_flow():
    """Test the EO Search tab flow"""

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

        # Save initial page
        driver.save_screenshot('eo_test_1_initial.png')

        # STEP 1: Click EO Search tab
        print("=" * 60)
        print("STEP 1: Click EO Search Tab")
        print("=" * 60)

        try:
            eo_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
            )
            print("✓ Found EO Search tab")
        except:
            eo_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "EO Search"))
            )
            print("✓ Found EO Search tab (partial match)")

        driver.execute_script("arguments[0].click();", eo_tab)
        time.sleep(3)
        print("✓ Clicked EO Search tab")

        driver.save_screenshot('eo_test_2_after_tab_click.png')

        # STEP 2: Find EO dropdown button
        print("\n" + "=" * 60)
        print("STEP 2: Find EO Dropdown Button")
        print("=" * 60)

        # Try multiple possible button IDs
        button_ids = [
            "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnExecutiveOrders",
            "ctl00_MainContent_UCEOSearch_btnExecutiveOrders",
            "btnExecutiveOrders"
        ]

        eo_button = None
        for button_id in button_ids:
            try:
                eo_button = driver.find_element(By.ID, button_id)
                print(f"✓ Found button with ID: {button_id}")
                break
            except:
                print(f"✗ Button not found with ID: {button_id}")

        if not eo_button:
            # Try by text
            try:
                eo_button = driver.find_element(By.XPATH, "//button[contains(text(), 'Executive')]")
                print("✓ Found button by text")
            except:
                print("✗ Could not find EO button by any method")

                # Save page source for debugging
                with open('eo_test_page_source.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("✓ Saved page source to eo_test_page_source.html")

                input("\nPress Enter to close...")
                return

        # Click the button
        print("\n" + "=" * 60)
        print("STEP 3: Click EO Dropdown Button")
        print("=" * 60)

        driver.execute_script("arguments[0].click();", eo_button)
        time.sleep(2)
        print("✓ Clicked EO dropdown button")

        driver.save_screenshot('eo_test_3_after_dropdown_click.png')

        # STEP 4: Find EO links
        print("\n" + "=" * 60)
        print("STEP 4: Extract EO Links")
        print("=" * 60)

        eo_links = driver.find_elements(
            By.XPATH,
            "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrExecutiveOrders')]"
        )

        print(f"Found {len(eo_links)} EO links")

        if eo_links:
            print("\nFirst 5 EO numbers:")
            for i, link in enumerate(eo_links[:5], 1):
                print(f"  {i}. {link.text.strip()}")

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print("\nCheck screenshots:")
        print("  - eo_test_1_initial.png")
        print("  - eo_test_2_after_tab_click.png")
        print("  - eo_test_3_after_dropdown_click.png")

        input("\nPress Enter to close...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

        try:
            driver.save_screenshot('eo_test_error.png')
            with open('eo_test_error.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("\n✓ Saved error screenshots and HTML")
        except:
            pass

    finally:
        driver.quit()


if __name__ == "__main__":
    test_eo_flow()
