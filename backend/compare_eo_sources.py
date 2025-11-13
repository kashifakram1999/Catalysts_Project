#!/usr/bin/env python3
"""
Compare Executive Order numbers from PDF vs Website dropdown
"""
import re
from pathlib import Path
import PyPDF2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def extract_eo_from_pdf():
    """Extract all EO numbers from the PDF"""
    print("=" * 60)
    print("EXTRACTING EO NUMBERS FROM PDF")
    print("=" * 60)

    pdf_path = Path(__file__).parent / 'data' / 'Data.pdf'

    if not pdf_path.exists():
        print(f"❌ PDF not found at: {pdf_path}")
        return set()

    print(f"📄 Reading PDF: {pdf_path}")

    eo_numbers = set()

    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)
            print(f"📖 Total pages: {total_pages}")

            for page_num in range(total_pages):
                page = pdf_reader.pages[page_num]
                text = page.extract_text()

                # Find all EO numbers (pattern: D-###-### or D-###-##)
                matches = re.findall(r'D-\d+-\d+', text)
                eo_numbers.update(matches)

                if (page_num + 1) % 50 == 0:
                    print(f"  Processed {page_num + 1}/{total_pages} pages... ({len(eo_numbers)} EO numbers found)")

            print(f"\n✅ PDF Extraction Complete")
            print(f"   Found {len(eo_numbers)} unique EO numbers")

    except Exception as e:
        print(f"❌ Error reading PDF: {e}")
        return set()

    return eo_numbers


def extract_eo_from_website():
    """Extract all EO numbers from website dropdown"""
    print("\n" + "=" * 60)
    print("EXTRACTING EO NUMBERS FROM WEBSITE DROPDOWN")
    print("=" * 60)

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)
    eo_numbers = set()

    try:
        url = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
        print(f"🌐 Loading: {url}")
        driver.get(url)
        time.sleep(3)

        # Click on "EO Search" tab - try multiple selectors
        print("📋 Clicking EO Search tab...")
        try:
            # Try by link text first
            eo_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
            )
        except:
            # Try by partial link text
            eo_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "EO Search"))
            )

        driver.execute_script("arguments[0].click();", eo_tab)
        time.sleep(3)

        # Click on EO dropdown
        print("🔽 Opening EO dropdown...")
        eo_dropdown = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnExecutiveOrders"))
        )
        driver.execute_script("arguments[0].click();", eo_dropdown)
        time.sleep(2)

        # Get all EO links from dropdown
        print("📊 Extracting EO numbers from dropdown...")
        eo_links = driver.find_elements(
            By.XPATH,
            "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrExecutiveOrders')]"
        )

        print(f"   Found {len(eo_links)} EO links in dropdown")

        for link in eo_links:
            eo_text = link.text.strip()
            # Extract just the EO number (format: D-###-###)
            match = re.search(r'(D-\d+-\d+)', eo_text)
            if match:
                eo_numbers.add(match.group(1))

        print(f"✅ Website Extraction Complete")
        print(f"   Found {len(eo_numbers)} unique EO numbers")

    except Exception as e:
        print(f"❌ Error scraping website: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()

    return eo_numbers


def compare_eo_numbers(pdf_eos, web_eos):
    """Compare EO numbers from both sources"""
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS")
    print("=" * 60)

    # Numbers in both
    in_both = pdf_eos & web_eos

    # Numbers only in PDF
    only_pdf = pdf_eos - web_eos

    # Numbers only in Website
    only_web = web_eos - pdf_eos

    print(f"\n📊 STATISTICS:")
    print(f"   PDF has:        {len(pdf_eos):>6} EO numbers")
    print(f"   Website has:    {len(web_eos):>6} EO numbers")
    print(f"   In both:        {len(in_both):>6} EO numbers")
    print(f"   Only in PDF:    {len(only_pdf):>6} EO numbers")
    print(f"   Only in Web:    {len(only_web):>6} EO numbers")

    # Coverage percentage
    if pdf_eos:
        pdf_coverage = (len(in_both) / len(pdf_eos)) * 100
        print(f"\n   Website covers {pdf_coverage:.1f}% of PDF EO numbers")

    if web_eos:
        web_coverage = (len(in_both) / len(web_eos)) * 100
        print(f"   PDF covers {web_coverage:.1f}% of Website EO numbers")

    # Show samples
    if only_pdf:
        print(f"\n📄 SAMPLE EO NUMBERS ONLY IN PDF (first 10):")
        for eo in sorted(only_pdf)[:10]:
            print(f"   {eo}")
        if len(only_pdf) > 10:
            print(f"   ... and {len(only_pdf) - 10} more")

    if only_web:
        print(f"\n🌐 SAMPLE EO NUMBERS ONLY IN WEBSITE (first 10):")
        for eo in sorted(only_web)[:10]:
            print(f"   {eo}")
        if len(only_web) > 10:
            print(f"   ... and {len(only_web) - 10} more")

    # Verdict
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)

    if len(pdf_eos) == len(web_eos) and len(only_pdf) == 0 and len(only_web) == 0:
        print("✅ IDENTICAL: Both sources have exactly the same EO numbers")
    elif len(only_pdf) == 0 and len(only_web) > 0:
        print("🆕 Website has NEWER data (additional EO numbers not in PDF)")
    elif len(only_web) == 0 and len(only_pdf) > 0:
        print("📄 PDF has MORE data (additional EO numbers not on website)")
    else:
        print("🔀 DIFFERENT: Both sources have unique EO numbers")
        print("   → Recommendation: Use BOTH sources for complete coverage")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("EO NUMBER COMPARISON: PDF vs WEBSITE")
    print("=" * 60)

    # Extract from both sources
    pdf_eos = extract_eo_from_pdf()
    web_eos = extract_eo_from_website()

    # Compare
    if pdf_eos or web_eos:
        compare_eo_numbers(pdf_eos, web_eos)
    else:
        print("\n❌ Could not extract EO numbers from either source")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
