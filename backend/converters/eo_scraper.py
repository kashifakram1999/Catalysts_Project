#!/usr/bin/env python3
"""
CARB Website Scraper - EO Number Based Approach
Scrapes catalytic converter data by searching each Executive Order number
"""

import time
import re
import logging
from typing import List, Dict, Optional
from datetime import datetime

from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

from .models import Manufacturer, CatalyticConverter

logger = logging.getLogger(__name__)


class CARBEOScraper:
    """Scrapes CARB data by searching Executive Order numbers"""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    def __init__(self, headless: bool = True, timeout: int = 20, pages_per_eo: int = 3):
        """
        Initialize the EO-based scraper

        Args:
            headless: Run browser in headless mode
            timeout: Timeout for element waits in seconds
            pages_per_eo: Number of pages to scrape per EO (default: 3)
        """
        self.headless = headless
        self.timeout = timeout
        self.pages_per_eo = pages_per_eo
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome WebDriver"""
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')

        self.driver = webdriver.Chrome(options=options)
        logger.info("WebDriver initialized")

    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            self.driver.quit()
            logger.info("WebDriver closed")

    def extract_eo_numbers(self) -> List[str]:
        """
        Extract all EO numbers from the website dropdown

        Returns:
            List of EO numbers (e.g., ['D-393-143', 'D-393-144', ...])
        """
        logger.info("=" * 60)
        logger.info("EXTRACTING EO NUMBERS FROM WEBSITE DROPDOWN")
        logger.info("=" * 60)

        eo_numbers = []

        try:
            # Navigate to website
            logger.info(f"Loading: {self.BASE_URL}")
            self.driver.get(self.BASE_URL)
            time.sleep(3)

            # Click on "EO Search" tab
            logger.info("Clicking EO Search tab...")
            try:
                eo_tab = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
                )
            except:
                eo_tab = WebDriverWait(self.driver, self.timeout).until(
                    EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "EO Search"))
                )

            self.driver.execute_script("arguments[0].click();", eo_tab)
            time.sleep(3)
            logger.info("EO Search tab clicked")

            # Click on EO dropdown button
            logger.info("Opening EO dropdown...")
            eo_dropdown = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"))
            )
            self.driver.execute_script("arguments[0].click();", eo_dropdown)
            time.sleep(2)
            logger.info("EO dropdown opened")

            # Extract all EO links from dropdown
            logger.info("Extracting EO numbers from dropdown...")
            eo_links = self.driver.find_elements(
                By.XPATH,
                "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers')]"
            )

            logger.info(f"Found {len(eo_links)} EO links in dropdown")

            for link in eo_links:
                eo_text = link.text.strip()
                # Extract just the EO number (format: D-###-###)
                match = re.search(r'(D-\d+-\d+)', eo_text)
                if match:
                    eo_number = match.group(1)
                    eo_numbers.append(eo_number)

            logger.info(f"✓ Extracted {len(eo_numbers)} unique EO numbers")

        except Exception as e:
            logger.error(f"Error extracting EO numbers: {e}")
            import traceback
            traceback.print_exc()

        return eo_numbers

    def _search_by_eo(self, eo_number: str) -> bool:
        """
        Search for a specific EO number

        Args:
            eo_number: EO number to search (e.g., 'D-393-143')

        Returns:
            True if search was successful, False otherwise
        """
        try:
            logger.info(f"Searching for EO: {eo_number}")

            # Make sure we're on EO Search tab
            try:
                eo_tab = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
                )
                self.driver.execute_script("arguments[0].click();", eo_tab)
                time.sleep(2)
            except:
                pass  # Already on EO Search tab

            # Click EO dropdown
            eo_dropdown = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"))
            )
            self.driver.execute_script("arguments[0].click();", eo_dropdown)
            time.sleep(1)

            # Find and click the specific EO link
            eo_xpath = f"//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') and contains(text(), '{eo_number}')]"
            eo_link = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.XPATH, eo_xpath))
            )

            # Extract postback parameters
            href = eo_link.get_attribute('href')
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)

            if match:
                target = match.group(1)
                argument = match.group(2)

                # Set hidden fields and submit (bypasses strict mode)
                self.driver.execute_script(f"""
                    var theForm = document.forms[0];
                    theForm.__EVENTTARGET.value = '{target}';
                    theForm.__EVENTARGUMENT.value = '{argument}';
                    theForm.submit();
                """)
                logger.info(f"✓ Triggered postback for {eo_number}")
            else:
                # Fallback: direct click
                self.driver.execute_script("arguments[0].click();", eo_link)
                logger.info(f"✓ Clicked {eo_number} (fallback)")

            # Wait for page to update after EO selection
            time.sleep(3)

            # IMPORTANT: After EO selection postback, page reverts to Vehicle Search tab
            # We need to click EO Search tab again
            logger.info(f"Clicking EO Search tab again (page reverted after postback)")
            try:
                eo_tab = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
                )
                self.driver.execute_script("arguments[0].click();", eo_tab)
                time.sleep(2)
                logger.info(f"✓ Back on EO Search tab")
            except:
                logger.warning("Could not click EO Search tab again")

            # Click the EO Search button
            logger.info(f"Clicking Search button for {eo_number}")
            search_button = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnEOSearch"))
            )
            self.driver.execute_script("arguments[0].click();", search_button)
            logger.info(f"✓ Clicked Search button")

            # Wait for results to load
            time.sleep(10)

            # Check if results table exists
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData"))
                )
                logger.info(f"✓ Results loaded for {eo_number}")
                return True
            except TimeoutException:
                logger.warning(f"No results table found for {eo_number}")
                return False

        except Exception as e:
            logger.error(f"Error searching for {eo_number}: {e}")
            return False

    def _extract_page_data(self, eo_number: str) -> List[Dict]:
        """
        Extract converter data from current results page

        Args:
            eo_number: EO number being scraped

        Returns:
            List of converter dictionaries
        """
        converters = []

        try:
            # Find results table
            table = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")

            # Get all data rows (skip header)
            rows = table.find_elements(By.XPATH, ".//tr[td]")

            logger.info(f"Found {len(rows)} rows on current page")

            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) >= 14:
                        # Extract data from each column (14 columns total)
                        # Column order: Make, Model Year, Model, Engine Size, Application Type,
                        # Part Manufacturer, Manufacturer Part Number, Test Group Name, Cert Level,
                        # Executive Order, Vehicle Class, Total Converters, Catalyst Location, Catalyst Part Type

                        # Parse model year start and end
                        model_year = cells[1].text.strip()
                        try:
                            model_year_start = int(model_year) if model_year else None
                        except:
                            model_year_start = None

                        # Parse quantity
                        total_converters = cells[11].text.strip()
                        try:
                            quantity = int(total_converters) if total_converters.isdigit() else None
                        except:
                            quantity = None

                        converter_data = {
                            'executive_order': eo_number,
                            'make': cells[0].text.strip(),
                            'model_year_start': model_year_start,
                            'model_year_end': model_year_start,  # Same as start for single year
                            'model': cells[2].text.strip(),
                            'engine_size': cells[3].text.strip(),
                            'application_type': cells[4].text.strip(),
                            'manufacturer_name': cells[5].text.strip(),
                            # CARB table labels this as Manufacturer Part Number, but our UI maps it to Series/Model.
                            # Store it in both fields so downstream consumers can rely on either naming.
                            'series_model': cells[6].text.strip(),
                            'part_number': cells[6].text.strip(),
                            'test_group': cells[7].text.strip(),
                            'cert_level': cells[8].text.strip(),
                            # cells[9] is Executive Order (already have it as eo_number)
                            'vehicle_class': cells[10].text.strip(),
                            'quantity': quantity,
                            'converter_location': cells[12].text.strip(),
                            'converter_type': cells[13].text.strip(),
                        }

                        converters.append(converter_data)

                except Exception as e:
                    logger.warning(f"Error parsing row: {e}")
                    continue

            logger.info(f"Extracted {len(converters)} converters from current page")

        except NoSuchElementException:
            logger.warning("Results table not found")
        except Exception as e:
            logger.error(f"Error extracting page data: {e}")

        return converters

    def _click_next_results_page(self) -> bool:
        """
        Click the "Next" pagination control for the results table.

        Returns:
            True if navigation succeeded, False otherwise
        """
        table_locator = (By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")
        next_selectors = [
            "//a[contains(@href, \"Page$Next\")]",
            "//a[contains(@title, 'Next')]",
            "//a[normalize-space(text())='Next']",
            "//a[normalize-space(text())='>']",
            "//a[contains(@class, 'next')]",
        ]

        try:
            current_table = self.driver.find_element(*table_locator)
        except NoSuchElementException:
            logger.warning("Cannot paginate because results table is missing")
            return False

        for xpath in next_selectors:
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            except TimeoutException:
                continue

            if next_button.tag_name.lower() == "span":
                continue

            button_classes = (next_button.get_attribute("class") or "").lower()
            aria_disabled = (next_button.get_attribute("aria-disabled") or "").lower()
            if "disabled" in button_classes or aria_disabled == "true":
                continue

            href = next_button.get_attribute("href") or ""
            if "__doPostBack" in href:
                match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                if match:
                    target, argument = match.groups()
                    logger.info("Triggering pagination postback to Next page")
                    self.driver.execute_script(f"""
                        var theForm = document.forms[0];
                        theForm.__EVENTTARGET.value = '{target}';
                        theForm.__EVENTARGUMENT.value = '{argument}';
                        theForm.submit();
                    """)
                else:
                    logger.info("Pagination href uses postback but pattern did not match, clicking directly")
                    self.driver.execute_script("arguments[0].click();", next_button)
            else:
                logger.info("Clicking Next pagination button")
                self.driver.execute_script("arguments[0].click();", next_button)

            try:
                WebDriverWait(self.driver, self.timeout).until(EC.staleness_of(current_table))
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located(table_locator)
                )
                time.sleep(2)
                logger.info("✓ Pagination successful")
                return True
            except TimeoutException:
                logger.warning("Next page did not load after clicking, trying other selector")
                continue

        logger.info("No enabled Next pagination control found")
        return False

    def _extract_multiple_pages(self, eo_number: str) -> List[Dict]:
        """
        Extract data from multiple pages for a given EO

        Args:
            eo_number: EO number being scraped

        Returns:
            List of all converters from all pages
        """
        all_converters = []
        page_num = 1

        logger.info(f"Extracting up to {self.pages_per_eo} pages for {eo_number}")

        while page_num <= self.pages_per_eo:
            logger.info(f"Processing page {page_num} for {eo_number}")

            # Extract current page data
            page_converters = self._extract_page_data(eo_number)

            if not page_converters:
                logger.info(f"No data on page {page_num}, stopping pagination")
                break

            all_converters.extend(page_converters)

            # Check if we should continue to next page
            if page_num < self.pages_per_eo:
                if self._click_next_results_page():
                    page_num += 1
                else:
                    logger.info("Pagination stopped before reaching configured page limit")
                    break
            else:
                logger.info(f"Reached maximum pages ({self.pages_per_eo})")
                break

        logger.info(f"✓ Total converters extracted for {eo_number}: {len(all_converters)}")
        return all_converters

    def scrape_by_eo_numbers(self, eo_numbers: List[str] = None) -> Dict[str, int]:
        """
        Scrape data for specified EO numbers (or all if None)

        Args:
            eo_numbers: List of EO numbers to scrape, or None to scrape all

        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_eos': 0,
            'successful_eos': 0,
            'failed_eos': 0,
            'total_converters': 0,
            'created': 0,
            'updated': 0
        }

        try:
            self._setup_driver()

            # Load the page first
            self.driver.get(self.BASE_URL)
            time.sleep(3)

            # Get EO numbers if not provided
            if eo_numbers is None:
                eo_numbers = self.extract_eo_numbers()

            stats['total_eos'] = len(eo_numbers)

            logger.info("=" * 60)
            logger.info(f"STARTING SCRAPE FOR {stats['total_eos']} EO NUMBERS")
            logger.info(f"Pages per EO: {self.pages_per_eo}")
            logger.info("=" * 60)

            for idx, eo_number in enumerate(eo_numbers, 1):
                logger.info(f"\n[{idx}/{stats['total_eos']}] Processing EO: {eo_number}")

                # Search for this EO
                if not self._search_by_eo(eo_number):
                    logger.warning(f"Failed to search {eo_number}")
                    stats['failed_eos'] += 1
                    continue

                # Extract data from multiple pages
                converters = self._extract_multiple_pages(eo_number)

                if converters:
                    stats['successful_eos'] += 1
                    stats['total_converters'] += len(converters)

                    # Save to database
                    created, updated = self._save_converters(converters)
                    stats['created'] += created
                    stats['updated'] += updated

                    logger.info(f"✓ Saved {created} new, {updated} updated for {eo_number}")
                else:
                    logger.warning(f"No converters found for {eo_number}")
                    stats['failed_eos'] += 1

                # Brief pause between EOs
                time.sleep(2)

            logger.info("\n" + "=" * 60)
            logger.info("SCRAPING COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total EOs processed: {stats['total_eos']}")
            logger.info(f"Successful: {stats['successful_eos']}")
            logger.info(f"Failed: {stats['failed_eos']}")
            logger.info(f"Total converters found: {stats['total_converters']}")
            logger.info(f"Created: {stats['created']}")
            logger.info(f"Updated: {stats['updated']}")

        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._close_driver()

        return stats

    def _save_converters(self, converters: List[Dict]) -> tuple:
        """
        Save converter data to database

        Args:
            converters: List of converter dictionaries

        Returns:
            Tuple of (created_count, updated_count)
        """
        created_count = 0
        updated_count = 0

        for data in converters:
            try:
                # Get or create manufacturer
                manufacturer_name = data.pop('manufacturer_name', 'Unknown')
                manufacturer, _ = Manufacturer.objects.get_or_create(
                    name=manufacturer_name
                )

                # Prepare converter data
                eo_number = data.get('executive_order')
                test_group = data.get('test_group', '')

                # Try to find existing converter
                existing = CatalyticConverter.objects.filter(
                    executive_order=eo_number,
                    test_group=test_group
                ).first()

                if existing:
                    # Update existing
                    for key, value in data.items():
                        if key != 'scraped_at' and value:
                            setattr(existing, key, value)
                    existing.manufacturer = manufacturer
                    existing.last_scraped = timezone.now()
                    existing.save()
                    updated_count += 1
                else:
                    # Create new
                    CatalyticConverter.objects.create(
                        manufacturer=manufacturer,
                        **data
                    )
                    created_count += 1

            except Exception as e:
                logger.error(f"Error saving converter: {e}")
                continue

        return created_count, updated_count
