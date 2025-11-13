#!/usr/bin/env python3
"""
Test to see exact EO table structure
"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

options = webdriver.ChromeOptions()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--window-size=1920,1080')

driver = webdriver.Chrome(options=options)

try:
    url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
    print(f"Loading: {url}")
    driver.get(url)
    time.sleep(3)

    # Click EO Search tab
    print("Clicking EO Search tab...")
    eo_tab = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
    )
    driver.execute_script("arguments[0].click();", eo_tab)
    time.sleep(3)

    # Click EO dropdown
    print("Opening EO dropdown...")
    eo_dropdown = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers")
    driver.execute_script("arguments[0].click();", eo_dropdown)
    time.sleep(2)

    # Click D-182-37
    print("Selecting D-182-37...")
    eo_link = driver.find_element(
        By.XPATH,
        "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') and contains(text(), 'D-182-37')]"
    )

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

    time.sleep(3)

    # Click EO Search tab again (page reverts)
    print("Clicking EO Search tab again...")
    eo_tab = driver.find_element(By.LINK_TEXT, "EO Search")
    driver.execute_script("arguments[0].click();", eo_tab)
    time.sleep(2)

    # Click Search button
    print("Clicking Search button...")
    search_button = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnEOSearch")
    driver.execute_script("arguments[0].click();", search_button)
    time.sleep(10)

    # Find table
    print("\n" + "="*80)
    table = driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")

    # Get headers
    headers = table.find_elements(By.XPATH, ".//tr/th")
    print("TABLE HEADERS:")
    print("="*80)
    for idx, header in enumerate(headers):
        print(f"Column {idx}: {header.text.strip()}")

    # Get first data row
    rows = table.find_elements(By.XPATH, ".//tr[td]")
    if rows:
        print("\n" + "="*80)
        print("FIRST DATA ROW:")
        print("="*80)
        cells = rows[0].find_elements(By.TAG_NAME, "td")
        for idx, cell in enumerate(cells):
            text = cell.text.strip()
            print(f"Cell {idx}: {text}")

        print(f"\nTotal columns: {len(cells)}")
        print(f"Total rows: {len(rows)}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

finally:
    time.sleep(5)
    driver.quit()
