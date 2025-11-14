#!/usr/bin/env python3
"""
TEST VERSION - CARB Website Scraper with Fixed Pagination
This test file implements automatic pagination detection instead of hard page limits
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


class CARBEOScraperTest:
    """TEST VERSION: Scrapes CARB data with auto-pagination detection"""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    def __init__(self, headless: bool = True, timeout: int = 20, pages_per_eo: Optional[int] = None):
        """
        Initialize the EO-based scraper (TEST VERSION)

        Args:
            headless: Run browser in headless mode
            timeout: Timeout for element waits in seconds
            pages_per_eo: Maximum pages to scrape per EO (None or 0 = unlimited, scrape all available pages)
        """
        self.headless = headless
        self.timeout = timeout
        # If None or 0, scrape all pages. Otherwise use as safety limit.
        self.pages_per_eo = pages_per_eo if pages_per_eo else None
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

    def _get_current_page_number(self) -> int:
        """
        Get the current active page number from pagination controls.

        Returns:
            Current page number (1-based), or 1 if cannot determine
        """
        if not self.driver:
            return 1

        try:
            # The current page is shown as a span (not inside an anchor) in the pagination row
            # All other page numbers are anchor tags, but the current page is just a span
            spans = self.driver.find_elements(
                By.XPATH,
                "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//td//span"
            )

            # Find the span that contains just a number (the current page)
            for span in spans:
                text = span.text.strip()
                if text.isdigit():
                    current_page = int(text)
                    logger.info(f"Current page: {current_page}")
                    return current_page

            # Fallback: assume page 1
            logger.warning("Could not determine current page from spans, assuming page 1")
            return 1
        except Exception as e:
            # Fallback: assume page 1
            logger.warning(f"Could not determine current page (error: {e}), assuming page 1")
            return 1

    def _click_next_results_page(self, current_page: Optional[int] = None) -> bool:
        """
        Click the next numbered page button in pagination.
        CARB uses numbered pagination (1, 2, 3...) instead of Next/Previous buttons.

        Args:
            current_page: Current page number (if known), otherwise will try to detect

        Returns:
            True if navigation succeeded, False if no more pages exist
        """
        table_locator = (By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")

        try:
            current_table = self.driver.find_element(*table_locator)
        except NoSuchElementException:
            logger.warning("Cannot paginate because results table is missing")
            return False

        if not self.driver:
            return False

        try:

            # Use provided current page or detect it
            if current_page is None:
                current_page = self._get_current_page_number()
            next_page = current_page + 1

            logger.info(f"Current page: {current_page}, looking for page: {next_page}")

            logger.info(f"Looking for page {next_page} button...")

            # Try to find the next page number button in the last row of the table
            # The pagination is at the bottom of the results table
            next_page_xpath = f"//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//a[normalize-space(text())='{next_page}']"

            next_page_button = None
            try:
                next_page_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, next_page_xpath))
                )

                # IMPORTANT: Scroll to the pagination button to make it visible
                logger.info(f"Scrolling to page {next_page} button...")
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_button)
                time.sleep(1)  # Wait for scroll to complete

            except TimeoutException:
                # Page button not found - might be on page 10+ with ellipsis (...)
                # IMPORTANT: Clicking ellipsis IS the navigation itself (not just revealing more numbers)
                logger.info(f"Page {next_page} button not directly visible, looking for ellipsis (...) button")

                pagination_row_xpath = "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]"
                try:
                    pagination_row = self.driver.find_element(By.XPATH, pagination_row_xpath)
                    ellipsis_button = None
                    passed_current_page = False

                    # Walk the pagination controls in order so we only consider ellipsis AFTER the current page.
                    pagination_controls = pagination_row.find_elements(By.XPATH, ".//a | .//span")
                    for control in pagination_controls:
                        text = control.text.strip()
                        if not text:
                            continue

                        if not passed_current_page and text == str(current_page):
                            passed_current_page = True
                            continue

                        if passed_current_page and text == "..." and control.tag_name.lower() == "a":
                            ellipsis_button = control
                            break

                    if not ellipsis_button:
                        logger.info("No forward ellipsis found after current page; reached the end of pagination")
                        raise NoSuchElementException("No forward ellipsis buttons found after the current page")

                    logger.info("Using forward ellipsis button to reveal additional pages")

                    # Scroll to and click the ellipsis
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ellipsis_button)
                    time.sleep(1)

                    # Extract the postback from ellipsis button
                    href = ellipsis_button.get_attribute("href") or ""
                    if "__doPostBack" in href:
                        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                        if match:
                            target, argument = match.groups()
                            logger.info(f"Clicking ellipsis via postback to navigate to page {next_page}")
                            self.driver.execute_script(f"""
                                var theForm = document.forms[0];
                                theForm.__EVENTTARGET.value = '{target}';
                                theForm.__EVENTARGUMENT.value = '{argument}';
                                theForm.submit();
                            """)
                        else:
                            logger.info(f"Clicking ellipsis directly")
                            self.driver.execute_script("arguments[0].click();", ellipsis_button)
                    else:
                        logger.info(f"Clicking ellipsis directly")
                        self.driver.execute_script("arguments[0].click();", ellipsis_button)

                    # Wait for page to reload after clicking ellipsis
                    try:
                        WebDriverWait(self.driver, self.timeout).until(EC.staleness_of(current_table))
                        time.sleep(2)

                        # IMPORTANT: Click EO Search tab again after ellipsis navigation
                        logger.info(f"Clicking EO Search tab again (page reverted after ellipsis)")
                        try:
                            eo_tab = WebDriverWait(self.driver, 10).until(
                                EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
                            )
                            self.driver.execute_script("arguments[0].click();", eo_tab)
                            time.sleep(2)
                            logger.info(f"✓ Back on EO Search tab")
                        except:
                            logger.warning("Could not click EO Search tab after ellipsis")

                        # Wait for table to appear again
                        WebDriverWait(self.driver, self.timeout).until(
                            EC.presence_of_element_located(table_locator)
                        )
                        time.sleep(2)

                        logger.info(f"✓ Successfully navigated to page {next_page} via ellipsis")
                        return True
                    except TimeoutException:
                        logger.warning(f"Page did not load after clicking ellipsis")
                        return False

                except NoSuchElementException:
                    logger.info(f"No ellipsis (...) button found, looking for Next (>) button")

                    # Try multiple possible "Next" button selectors
                    next_button_xpaths = [
                        "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//a[contains(text(), '>')]",
                        "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//a[contains(@title, 'Next')]",
                        "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//a[normalize-space(text())='Next']",
                    ]

                    next_page_button = None
                    for xpath in next_button_xpaths:
                        try:
                            next_button = self.driver.find_element(By.XPATH, xpath)

                            # Check if button is disabled
                            button_classes = (next_button.get_attribute("class") or "").lower()
                            if "disabled" in button_classes or next_button.tag_name.lower() == "span":
                                logger.info(f"Next button is disabled, no more pages")
                                return False

                            logger.info(f"Found Next (>) button")
                            next_page_button = next_button
                            break

                        except NoSuchElementException:
                            continue

                    if next_page_button is None:
                        logger.info(f"No Next button found, reached last page")
                        return False

            # Check if the button is actually clickable (not disabled)
            button_classes = (next_page_button.get_attribute("class") or "").lower()
            if "disabled" in button_classes:
                logger.info(f"Page {next_page} button is disabled, no more pages")
                return False

            # Extract and trigger the postback
            href = next_page_button.get_attribute("href") or ""
            if "__doPostBack" in href:
                match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                if match:
                    target, argument = match.groups()
                    logger.info(f"Clicking page {next_page} via postback")
                    self.driver.execute_script(f"""
                        var theForm = document.forms[0];
                        theForm.__EVENTTARGET.value = '{target}';
                        theForm.__EVENTARGUMENT.value = '{argument}';
                        theForm.submit();
                    """)
                else:
                    logger.info(f"Clicking page {next_page} directly")
                    self.driver.execute_script("arguments[0].click();", next_page_button)
            else:
                logger.info(f"Clicking page {next_page} directly")
                self.driver.execute_script("arguments[0].click();", next_page_button)

            # Wait for page to reload
            try:
                WebDriverWait(self.driver, self.timeout).until(EC.staleness_of(current_table))
                time.sleep(2)

                # IMPORTANT: After pagination postback, page reverts to Vehicle Search tab
                # We need to click EO Search tab again (same issue as when selecting EO initially)
                logger.info(f"Clicking EO Search tab again (page reverted after pagination)")
                try:
                    eo_tab = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
                    )
                    self.driver.execute_script("arguments[0].click();", eo_tab)
                    time.sleep(2)
                    logger.info(f"✓ Back on EO Search tab")
                except:
                    logger.warning("Could not click EO Search tab after pagination")

                # Now wait for the table to appear again
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located(table_locator)
                )
                time.sleep(2)  # Extra wait for page to stabilize

                logger.info(f"✓ Successfully navigated to page {next_page}")
                return True
            except TimeoutException:
                logger.warning(f"Page {next_page} did not load after clicking")
                return False

        except Exception as e:
            logger.error(f"Error during pagination: {e}")
            return False

    def _extract_multiple_pages(self, eo_number: str) -> List[Dict]:
        """
        Extract data from multiple pages for a given EO

        FIXED VERSION: Continues pagination until no "Next" button exists,
        instead of stopping at a hard page limit.

        Args:
            eo_number: EO number being scraped

        Returns:
            List of all converters from all pages
        """
        all_converters = []
        page_num = 1

        if self.pages_per_eo:
            logger.info(f"Extracting pages for {eo_number} (max limit: {self.pages_per_eo})")
        else:
            logger.info(f"Extracting all available pages for {eo_number} (no limit)")

        # Continue scraping until we run out of pages OR hit the optional safety limit
        while True:
            logger.info(f"Processing page {page_num} for {eo_number}")

            # Extract current page data
            page_converters = self._extract_page_data(eo_number)

            if not page_converters:
                logger.info(f"No data on page {page_num}, stopping pagination")
                break

            all_converters.extend(page_converters)
            logger.info(f"Total so far: {len(all_converters)} converters")

            # Check if we've hit the optional safety limit
            if self.pages_per_eo and page_num >= self.pages_per_eo:
                logger.info(f"Reached safety limit of {self.pages_per_eo} pages")
                break

            # Try to go to next page (pass current page number)
            if self._click_next_results_page(current_page=page_num):
                page_num += 1
            else:
                logger.info("No more pages available, pagination complete")
                break

        logger.info(f"✓ Total converters extracted for {eo_number}: {len(all_converters)} across {page_num} pages")
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
            logger.info(f"STARTING SCRAPE FOR {stats['total_eos']} EO NUMBERS (TEST VERSION)")
            if self.pages_per_eo:
                logger.info(f"Safety limit: {self.pages_per_eo} pages per EO")
            else:
                logger.info(f"No page limit - will scrape all available pages")
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
            logger.info("SCRAPING COMPLETE (TEST VERSION)")
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
