#!/usr/bin/env python3
"""
CARB Website Scraper - EO Number Based Approach with Enhanced Robustness
Scrapes catalytic converter data by searching each Executive Order number

Enhanced with:
- Per-EO retry logic with session recovery
- Dead session detection and automatic driver restart
- Robust distinction between "no results" and "technical failures"
- Pagination timeout handling with partial status support
- Comprehensive status tracking and logging
"""

import time
import re
import logging
from typing import List, Dict, Optional, Tuple

from django.utils import timezone

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    WebDriverException,
    NoSuchWindowException,
)

from .models import Manufacturer, CatalyticConverter

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# Maximum retry attempts per EO before giving up
MAX_EO_RETRIES = 3

# Timeout for explicit waits (seconds)
DEFAULT_WAIT_TIMEOUT = 30

# Longer timeout for initial page loads after postback
POSTBACK_WAIT_TIMEOUT = 45

# =============================================================================
# EO PROCESSING STATUS
# =============================================================================

class EOStatus:
    """Constants for EO processing status"""
    SUCCESS = "success"           # EO fully scraped
    FAILED = "failed"             # Technical failure (timeout, session death, etc.)
    NO_RESULTS = "no_results"     # EO has no data (legitimate empty result)
    PARTIAL = "partial"           # Partial scrape (pagination failed mid-way)


# =============================================================================
# SCRAPER CLASS
# =============================================================================

class CARBEOScraper:
    """Scrapes CARB data by searching Executive Order numbers with robust error handling"""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    def __init__(self, headless: bool = True, timeout: int = 20, pages_per_eo: Optional[int] = None):
        """
        Initialize the EO-based scraper

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

    # =========================================================================
    # DRIVER LIFECYCLE MANAGEMENT
    # =========================================================================

    def _setup_driver(self):
        """Setup Chrome WebDriver with stability options"""
        options = webdriver.ChromeOptions()

        # Basic options
        if self.headless:
            options.add_argument('--headless=new')  # Use new headless mode

        # Stability options
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')

        # Memory management
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-plugins')

        # Window size
        options.add_argument('--window-size=1920,1080')

        # Additional stability
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Page load strategy
        options.page_load_strategy = 'normal'

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(90)  # 90 second timeout for page loads
            logger.info("WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def _close_driver(self):
        """Close WebDriver safely"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver closed successfully")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None

    def _is_session_dead(self, exception: Exception) -> bool:
        """
        Check if an exception indicates a dead WebDriver session

        Args:
            exception: The exception to check

        Returns:
            True if session is dead, False otherwise
        """
        if not isinstance(exception, (WebDriverException, NoSuchWindowException)):
            return False

        error_msg = str(exception).lower()

        # Check for known dead session indicators
        dead_session_patterns = [
            'invalid session id',
            'session deleted',
            'session not created',
            'disconnected: not connected to devtools',
            'chrome not reachable',
            'no such window',
            'target window already closed',
        ]

        return any(pattern in error_msg for pattern in dead_session_patterns)

    def _recover_from_dead_session(self):
        """
        Recover from a dead WebDriver session by restarting the driver

        This method handles cleanup of the dead session and creates a fresh one.
        """
        logger.warning("Detected dead WebDriver session - recovering...")

        # Close the dead driver
        self._close_driver()

        # Wait a moment before restarting
        time.sleep(2)

        # Create new driver
        self._setup_driver()

        # Navigate to base page
        self.driver.get(self.BASE_URL)
        time.sleep(3)

        logger.info("Successfully recovered from dead session")

    # =========================================================================
    # ROBUST WAITING AND INTERACTION HELPERS
    # =========================================================================

    def _safe_wait_and_click(self, by, value, description="element", timeout=None):
        """
        Safely wait for an element and click it with multiple strategies

        Args:
            by: Selenium By locator type
            value: Locator value
            description: Human-readable description for logging
            timeout: Optional custom timeout

        Returns:
            True if successful, False otherwise
        """
        timeout = timeout or self.timeout

        try:
            # Wait for element to be clickable
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )

            # Try multiple click strategies
            try:
                # Strategy 1: Regular click
                element.click()
            except:
                try:
                    # Strategy 2: JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                except:
                    # Strategy 3: Action chains
                    from selenium.webdriver.common.action_chains import ActionChains
                    ActionChains(self.driver).move_to_element(element).click().perform()

            return True

        except TimeoutException:
            logger.error(f"Timeout waiting for {description}")
            return False
        except Exception as e:
            logger.error(f"Error clicking {description}: {e}")
            return False

    def _wait_for_eo_search_tab_active(self, timeout=None):
        """
        Wait for EO Search tab to be active and visible

        Args:
            timeout: Optional custom timeout

        Returns:
            True if tab is active, False otherwise
        """
        timeout = timeout or self.timeout

        try:
            # Click EO Search tab
            self._safe_wait_and_click(By.LINK_TEXT, "EO Search", "EO Search tab", timeout=timeout)
            time.sleep(2)

            # Verify the tab content loaded by checking for the input field
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"))
            )

            return True
        except:
            return False

    # =========================================================================
    # EO NUMBER EXTRACTION
    # =========================================================================

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

    # =========================================================================
    # SINGLE EO SCRAPING (INTERNAL - CALLED BY RETRY LOGIC)
    # =========================================================================

    def _scrape_single_eo(self, eo_number: str) -> Tuple[str, List[Dict], Optional[str]]:
        """
        Scrape a single EO number (internal method, no retry logic)

        This is the core scraping logic for one EO, called by process_eo_with_retries().
        It does NOT handle retries or session recovery - that's handled by the caller.

        Args:
            eo_number: The EO number to scrape

        Returns:
            Tuple of (status, converters_list, error_message)
            - status: One of EOStatus constants
            - converters_list: List of converter dicts (empty if failed/no_results)
            - error_message: Error description if failed, None otherwise
        """
        try:
            # Step 1: Search for the EO
            search_result = self._search_by_eo_robust(eo_number)

            if search_result['status'] == 'no_results':
                logger.info(f"EO {eo_number} | status={EOStatus.NO_RESULTS}")
                return EOStatus.NO_RESULTS, [], None

            elif search_result['status'] == 'error':
                error_msg = search_result.get('error', 'Unknown search error')
                logger.warning(f"EO {eo_number} | status=search_failed | error={error_msg}")
                return EOStatus.FAILED, [], error_msg

            # Step 2: Extract data from all pages
            pagination_result = self._extract_multiple_pages_robust(eo_number)

            converters = pagination_result['converters']

            if pagination_result['status'] == 'complete':
                logger.info(f"EO {eo_number} | status={EOStatus.SUCCESS} | converters={len(converters)}")
                return EOStatus.SUCCESS, converters, None

            elif pagination_result['status'] == 'partial':
                reason = pagination_result.get('error', 'pagination_timeout')
                logger.warning(f"EO {eo_number} | status={EOStatus.PARTIAL} | reason={reason} | converters={len(converters)}")
                return EOStatus.PARTIAL, converters, f"partial: {reason}"

            else:  # error
                error_msg = pagination_result.get('error', 'pagination_error')
                logger.error(f"EO {eo_number} | status={EOStatus.FAILED} | error={error_msg}")
                return EOStatus.FAILED, [], error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"EO {eo_number} | status={EOStatus.FAILED} | error={error_msg}")
            return EOStatus.FAILED, [], error_msg

    def _search_by_eo_robust(self, eo_number: str) -> Dict:
        """
        Search for a specific EO number with robust error handling

        This method explicitly distinguishes between:
        - Successful search with results table visible
        - Legitimate "no results" (no data for this EO)
        - Technical failure (timeout, element not found, etc.)

        Args:
            eo_number: EO number to search (e.g., 'D-393-143')

        Returns:
            Dict with keys:
            - status: 'success', 'no_results', or 'error'
            - error: error message if status is 'error'
        """
        try:
            logger.info(f"Searching for EO: {eo_number}")

            # Ensure we're on EO Search tab
            if not self._wait_for_eo_search_tab_active(timeout=15):
                return {'status': 'error', 'error': 'Failed to activate EO Search tab'}

            # Click EO dropdown
            try:
                eo_dropdown = WebDriverWait(self.driver, DEFAULT_WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"))
                )
                self.driver.execute_script("arguments[0].click();", eo_dropdown)
                time.sleep(1)
            except TimeoutException:
                return {'status': 'error', 'error': 'EO dropdown button not found'}

            # Find and click the specific EO link
            eo_xpath = f"//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') and contains(text(), '{eo_number}')]"

            try:
                eo_link = WebDriverWait(self.driver, DEFAULT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.XPATH, eo_xpath))
                )
            except TimeoutException:
                return {'status': 'error', 'error': f'EO {eo_number} not found in dropdown'}

            # Extract postback parameters and trigger
            href = eo_link.get_attribute('href')
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)

            if match:
                target = match.group(1)
                argument = match.group(2)

                # Set hidden fields and submit
                self.driver.execute_script(f"""
                    var theForm = document.forms[0];
                    theForm.__EVENTTARGET.value = '{target}';
                    theForm.__EVENTARGUMENT.value = '{argument}';
                    theForm.submit();
                """)
                logger.info(f"Triggered postback for {eo_number}")
            else:
                # Fallback: direct click
                self.driver.execute_script("arguments[0].click();", eo_link)
                logger.info(f"Clicked {eo_number} (fallback)")

            # Wait for page to update after EO selection
            time.sleep(3)

            # After EO selection postback, page reverts to Vehicle Search tab
            # Click EO Search tab again
            logger.info("Returning to EO Search tab after postback...")
            if not self._wait_for_eo_search_tab_active(timeout=POSTBACK_WAIT_TIMEOUT):
                return {'status': 'error', 'error': 'Failed to return to EO Search tab after postback'}

            # Click the EO Search button
            logger.info(f"Clicking Search button for {eo_number}")
            try:
                search_button = WebDriverWait(self.driver, DEFAULT_WAIT_TIMEOUT).until(
                    EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnEOSearch"))
                )
                self.driver.execute_script("arguments[0].click();", search_button)
                logger.info("Clicked Search button")
            except TimeoutException:
                return {'status': 'error', 'error': 'Search button not found'}

            # Wait for results - use explicit wait for either results table OR no-results message
            time.sleep(5)  # Initial wait for postback

            # Check for results table
            results_table_id = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData"

            try:
                # Wait for results table to appear
                WebDriverWait(self.driver, POSTBACK_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.ID, results_table_id))
                )

                # Verify table has data rows (not just header)
                time.sleep(2)
                table = self.driver.find_element(By.ID, results_table_id)
                data_rows = table.find_elements(By.XPATH, ".//tr[td]")

                if data_rows:
                    logger.info(f"Results loaded for {eo_number} ({len(data_rows)} rows visible)")
                    return {'status': 'success'}
                else:
                    # Table exists but no data rows - treat as no results
                    logger.info(f"Results table found but empty for {eo_number}")
                    return {'status': 'no_results'}

            except TimeoutException:
                # Table didn't appear - could be legitimate "no results" or error
                # Check for common "no results" indicators
                try:
                    # Look for any message indicating no results
                    no_results_indicators = [
                        "//span[contains(text(), 'No records')]",
                        "//div[contains(text(), 'No records')]",
                        "//span[contains(text(), 'no data')]",
                        "//div[contains(text(), 'no data')]",
                    ]

                    for indicator in no_results_indicators:
                        try:
                            self.driver.find_element(By.XPATH, indicator)
                            logger.info(f"No results message found for {eo_number}")
                            return {'status': 'no_results'}
                        except NoSuchElementException:
                            continue

                    # No table and no "no results" message - likely a technical issue
                    logger.warning(f"No results table or message found for {eo_number}")
                    return {'status': 'error', 'error': 'Results table not found after search'}

                except:
                    return {'status': 'error', 'error': 'Results table not found after search'}

        except WebDriverException as e:
            error_msg = f"WebDriver error: {str(e)}"
            logger.error(f"Error searching for {eo_number}: {error_msg}")
            return {'status': 'error', 'error': error_msg}
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Error searching for {eo_number}: {error_msg}")
            return {'status': 'error', 'error': error_msg}

    # =========================================================================
    # DATA EXTRACTION AND PAGINATION
    # =========================================================================

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
                            'model_year_end': model_year_start,
                            'model': cells[2].text.strip(),
                            'engine_size': cells[3].text.strip(),
                            'application_type': cells[4].text.strip(),
                            'manufacturer_name': cells[5].text.strip(),
                            'series_model': cells[6].text.strip(),
                            'part_number': cells[6].text.strip(),
                            'test_group': cells[7].text.strip(),
                            'cert_level': cells[8].text.strip(),
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
        Get the current active page number from pagination controls

        Returns:
            Current page number (1-based), or 1 if cannot determine
        """
        if not self.driver:
            return 1

        try:
            spans = self.driver.find_elements(
                By.XPATH,
                "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//td//span"
            )

            for span in spans:
                text = span.text.strip()
                if text.isdigit():
                    current_page = int(text)
                    return current_page

            return 1
        except Exception as e:
            return 1

    def _click_next_results_page(self, current_page: Optional[int] = None, eo_number: str = "") -> bool:
        """
        Click the next numbered page button in pagination with robust error handling

        Args:
            current_page: Current page number (if known), otherwise will try to detect
            eo_number: EO number being scraped (for logging)

        Returns:
            True if navigation succeeded, False if no more pages exist

        Raises:
            WebDriverException: If a timeout or driver error occurs during pagination
        """
        table_locator = (By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData")

        try:
            current_table = self.driver.find_element(*table_locator)
        except NoSuchElementException:
            logger.warning(f"[{eo_number}] Cannot paginate - results table missing")
            return False

        if not self.driver:
            return False

        try:
            # Use provided current page or detect it
            if current_page is None:
                current_page = self._get_current_page_number()
            next_page = current_page + 1

            logger.info(f"[{eo_number}] Current page: {current_page}, navigating to page {next_page}")

            # Try to find the next page number button
            next_page_xpath = f"//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]//a[normalize-space(text())='{next_page}']"

            next_page_button = None
            try:
                next_page_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, next_page_xpath))
                )

                # Scroll to the pagination button
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_button)
                time.sleep(1)

            except TimeoutException:
                # Page button not visible - try ellipsis
                logger.info(f"[{eo_number}] Page {next_page} button not visible, looking for ellipsis")

                pagination_row_xpath = "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]"
                try:
                    pagination_row = self.driver.find_element(By.XPATH, pagination_row_xpath)
                    ellipsis_button = None
                    passed_current_page = False

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
                        logger.info(f"[{eo_number}] No more pages - reached end of pagination")
                        return False

                    logger.info(f"[{eo_number}] Clicking ellipsis to reveal more pages")

                    # Scroll and click ellipsis
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", ellipsis_button)
                    time.sleep(1)

                    href = ellipsis_button.get_attribute("href") or ""
                    if "__doPostBack" in href:
                        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                        if match:
                            target, argument = match.groups()
                            self.driver.execute_script(f"""
                                var theForm = document.forms[0];
                                theForm.__EVENTTARGET.value = '{target}';
                                theForm.__EVENTARGUMENT.value = '{argument}';
                                theForm.submit();
                            """)
                        else:
                            self.driver.execute_script("arguments[0].click();", ellipsis_button)
                    else:
                        self.driver.execute_script("arguments[0].click();", ellipsis_button)

                    # Wait for page reload - use longer timeout for renderer issues
                    WebDriverWait(self.driver, POSTBACK_WAIT_TIMEOUT).until(EC.staleness_of(current_table))
                    time.sleep(2)

                    # Return to EO Search tab
                    self._wait_for_eo_search_tab_active(timeout=POSTBACK_WAIT_TIMEOUT)

                    # Wait for table
                    WebDriverWait(self.driver, POSTBACK_WAIT_TIMEOUT).until(
                        EC.presence_of_element_located(table_locator)
                    )
                    time.sleep(2)

                    logger.info(f"[{eo_number}] Successfully navigated via ellipsis")
                    return True

                except NoSuchElementException:
                    logger.info(f"[{eo_number}] No ellipsis or next button - end of pagination")
                    return False

            # Check if button is disabled
            if next_page_button:
                button_classes = (next_page_button.get_attribute("class") or "").lower()
                if "disabled" in button_classes:
                    logger.info(f"[{eo_number}] Next page button is disabled - end of pagination")
                    return False

                # Click the page button
                href = next_page_button.get_attribute("href") or ""
                if "__doPostBack" in href:
                    match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
                    if match:
                        target, argument = match.groups()
                        self.driver.execute_script(f"""
                            var theForm = document.forms[0];
                            theForm.__EVENTTARGET.value = '{target}';
                            theForm.__EVENTARGUMENT.value = '{argument}';
                            theForm.submit();
                        """)
                    else:
                        self.driver.execute_script("arguments[0].click();", next_page_button)
                else:
                    self.driver.execute_script("arguments[0].click();", next_page_button)

                # Wait for page reload - use longer timeout
                WebDriverWait(self.driver, POSTBACK_WAIT_TIMEOUT).until(EC.staleness_of(current_table))
                time.sleep(2)

                # Return to EO Search tab
                self._wait_for_eo_search_tab_active(timeout=POSTBACK_WAIT_TIMEOUT)

                # Wait for table
                WebDriverWait(self.driver, POSTBACK_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located(table_locator)
                )
                time.sleep(2)

                logger.info(f"[{eo_number}] Successfully navigated to page {next_page}")
                return True

            return False

        except TimeoutException as e:
            # Timeout during pagination - this is a critical error
            error_msg = f"Timeout during pagination to page {next_page}: {str(e)}"
            logger.error(f"[{eo_number}] {error_msg}")
            raise WebDriverException(error_msg)

        except WebDriverException as e:
            # Propagate WebDriver exceptions (including renderer timeouts)
            logger.error(f"[{eo_number}] WebDriver error during pagination: {e}")
            raise

        except Exception as e:
            error_msg = f"Unexpected error during pagination: {str(e)}"
            logger.error(f"[{eo_number}] {error_msg}")
            raise WebDriverException(error_msg)

    def _extract_multiple_pages_robust(self, eo_number: str) -> Dict:
        """
        Extract data from multiple pages with robust pagination error handling

        If pagination fails mid-way (timeout, renderer error, etc.), this method:
        - Keeps the data scraped so far
        - Returns status='partial' instead of failing completely

        Args:
            eo_number: EO number being scraped

        Returns:
            Dict with keys:
            - status: 'complete', 'partial', or 'error'
            - converters: List of converter dicts
            - error: Error message if status is 'partial' or 'error'
            - pages_scraped: Number of pages successfully scraped
        """
        all_converters = []
        page_num = 1

        if self.pages_per_eo:
            logger.info(f"Extracting pages for {eo_number} (max limit: {self.pages_per_eo})")
        else:
            logger.info(f"Extracting all available pages for {eo_number} (no limit)")

        try:
            while True:
                logger.info(f"Processing page {page_num} for {eo_number}")

                # Extract current page data
                try:
                    page_converters = self._extract_page_data(eo_number)
                except Exception as e:
                    logger.error(f"Error extracting data from page {page_num}: {e}")
                    # If we can't extract even the first page, it's a failure
                    if page_num == 1:
                        return {
                            'status': 'error',
                            'converters': [],
                            'error': f'Failed to extract page 1: {str(e)}',
                            'pages_scraped': 0
                        }
                    # If we fail on a later page, return what we have as partial
                    return {
                        'status': 'partial',
                        'converters': all_converters,
                        'error': f'extraction_error_on_page_{page_num}',
                        'pages_scraped': page_num - 1
                    }

                if not page_converters:
                    logger.info(f"No data on page {page_num}, stopping pagination")
                    break

                all_converters.extend(page_converters)
                logger.info(f"Total so far: {len(all_converters)} converters")

                # Check if we've hit the optional safety limit
                if self.pages_per_eo and page_num >= self.pages_per_eo:
                    logger.info(f"Reached safety limit of {self.pages_per_eo} pages")
                    # Mark as partial if we hit the limit
                    return {
                        'status': 'partial',
                        'converters': all_converters,
                        'error': f'hit_max_pages_limit_{self.pages_per_eo}',
                        'pages_scraped': page_num
                    }

                # Try to go to next page
                try:
                    if self._click_next_results_page(current_page=page_num, eo_number=eo_number):
                        page_num += 1
                    else:
                        # Natural end of pagination
                        logger.info(f"[{eo_number}] No more pages available, pagination complete")
                        break

                except WebDriverException as e:
                    # Pagination failed - timeout, renderer error, etc.
                    error_msg = str(e)

                    # Check if it's a renderer timeout
                    if 'renderer' in error_msg.lower() or 'timeout' in error_msg.lower():
                        logger.warning(f"[{eo_number}] Pagination timeout on page {page_num + 1}: {error_msg}")
                        # Return partial status with data collected so far
                        return {
                            'status': 'partial',
                            'converters': all_converters,
                            'error': f'pagination_timeout_on_page_{page_num + 1}',
                            'pages_scraped': page_num
                        }
                    else:
                        # Other WebDriver error during pagination
                        logger.error(f"[{eo_number}] Pagination error on page {page_num + 1}: {error_msg}")
                        return {
                            'status': 'partial',
                            'converters': all_converters,
                            'error': f'pagination_error_on_page_{page_num + 1}',
                            'pages_scraped': page_num
                        }

            # Successfully scraped all pages
            logger.info(f"Total converters extracted for {eo_number}: {len(all_converters)} across {page_num} pages")
            return {
                'status': 'complete',
                'converters': all_converters,
                'error': None,
                'pages_scraped': page_num
            }

        except Exception as e:
            # Unexpected error
            logger.error(f"Unexpected error during multi-page extraction for {eo_number}: {e}")
            if all_converters:
                # Return partial if we have some data
                return {
                    'status': 'partial',
                    'converters': all_converters,
                    'error': f'unexpected_error: {str(e)}',
                    'pages_scraped': page_num
                }
            else:
                # Total failure if no data
                return {
                    'status': 'error',
                    'converters': [],
                    'error': f'unexpected_error: {str(e)}',
                    'pages_scraped': 0
                }

    # =========================================================================
    # PER-EO RETRY LOGIC
    # =========================================================================

    def process_eo_with_retries(self, eo_number: str) -> Dict:
        """
        Process a single EO with retry logic and session recovery

        This is the main entry point for processing one EO. It handles:
        - Retries (up to MAX_EO_RETRIES)
        - Dead session detection and recovery
        - Distinguishing between different failure types

        Args:
            eo_number: The EO number to process

        Returns:
            Dict with keys:
            - eo_number: The EO number
            - status: One of EOStatus constants
            - converters: List of converter dicts (empty if failed/no_results)
            - error: Error message if failed, None otherwise
            - attempts: Number of attempts made
        """
        for attempt in range(1, MAX_EO_RETRIES + 1):
            try:
                if attempt > 1:
                    logger.info(f"Retry attempt {attempt}/{MAX_EO_RETRIES} for {eo_number}")

                # Attempt to scrape this EO
                status, converters, error = self._scrape_single_eo(eo_number)

                # Success or legitimate no_results - don't retry
                if status in [EOStatus.SUCCESS, EOStatus.NO_RESULTS]:
                    return {
                        'eo_number': eo_number,
                        'status': status,
                        'converters': converters,
                        'error': error,
                        'attempts': attempt
                    }

                # Partial - also don't retry, we have some data
                if status == EOStatus.PARTIAL:
                    return {
                        'eo_number': eo_number,
                        'status': status,
                        'converters': converters,
                        'error': error,
                        'attempts': attempt
                    }

                # Failed - retry if we have attempts left
                if attempt < MAX_EO_RETRIES:
                    logger.warning(f"EO {eo_number} failed (attempt {attempt}/{MAX_EO_RETRIES}), will retry...")
                    time.sleep(2)
                    continue
                else:
                    # Final attempt failed
                    logger.error(f"EO {eo_number} failed after {MAX_EO_RETRIES} attempts")
                    return {
                        'eo_number': eo_number,
                        'status': EOStatus.FAILED,
                        'converters': [],
                        'error': f"failed_after_{MAX_EO_RETRIES}_retries: {error}",
                        'attempts': attempt
                    }

            except WebDriverException as e:
                # Check if session is dead
                if self._is_session_dead(e):
                    logger.error(f"Dead session detected for {eo_number} (attempt {attempt}): {e}")

                    # Attempt recovery
                    try:
                        self._recover_from_dead_session()
                        logger.info(f"Session recovered, will retry {eo_number}")

                        # Retry on next iteration
                        if attempt < MAX_EO_RETRIES:
                            continue
                        else:
                            return {
                                'eo_number': eo_number,
                                'status': EOStatus.FAILED,
                                'converters': [],
                                'error': f"invalid_session_id_after_{MAX_EO_RETRIES}_retries",
                                'attempts': attempt
                            }
                    except Exception as recovery_error:
                        logger.error(f"Failed to recover from dead session: {recovery_error}")
                        return {
                            'eo_number': eo_number,
                            'status': EOStatus.FAILED,
                            'converters': [],
                            'error': f"session_recovery_failed: {str(recovery_error)}",
                            'attempts': attempt
                        }
                else:
                    # Other WebDriver exception
                    logger.error(f"WebDriver error for {eo_number} (attempt {attempt}): {e}")

                    if attempt < MAX_EO_RETRIES:
                        logger.info(f"Will retry {eo_number}")
                        time.sleep(2)
                        continue
                    else:
                        return {
                            'eo_number': eo_number,
                            'status': EOStatus.FAILED,
                            'converters': [],
                            'error': f"webdriver_error_after_{MAX_EO_RETRIES}_retries: {str(e)}",
                            'attempts': attempt
                        }

            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error for {eo_number} (attempt {attempt}): {e}")

                if attempt < MAX_EO_RETRIES:
                    logger.info(f"Will retry {eo_number}")
                    time.sleep(2)
                    continue
                else:
                    return {
                        'eo_number': eo_number,
                        'status': EOStatus.FAILED,
                        'converters': [],
                        'error': f"unexpected_error_after_{MAX_EO_RETRIES}_retries: {str(e)}",
                        'attempts': attempt
                    }

        # Should never reach here, but just in case
        return {
            'eo_number': eo_number,
            'status': EOStatus.FAILED,
            'converters': [],
            'error': 'max_retries_exceeded',
            'attempts': MAX_EO_RETRIES
        }

    # =========================================================================
    # DATABASE OPERATIONS
    # =========================================================================

    def _save_converters(self, converters: List[Dict]) -> Tuple[int, int]:
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

    # =========================================================================
    # MAIN SCRAPING ENTRY POINT (PUBLIC API)
    # =========================================================================

    def scrape_by_eo_numbers(self, eo_numbers: List[str] = None) -> Dict[str, int]:
        """
        Scrape data for specified EO numbers (or all if None)

        This is the main public API called by Celery tasks.
        Enhanced with robust retry logic and session recovery.

        Args:
            eo_numbers: List of EO numbers to scrape, or None to scrape all

        Returns:
            Dictionary with statistics including:
            - total_eos, successful_eos, failed_eos, no_results_eos, partial_eos
            - total_converters, created, updated
            - Lists of EOs by status
        """
        stats = {
            'total_eos': 0,
            'successful_eos': 0,
            'failed_eos': 0,
            'no_results_eos': 0,
            'partial_eos': 0,
            'total_converters': 0,
            'created': 0,
            'updated': 0,
            'successful_eo_list': [],
            'failed_eo_list': [],
            'no_results_eo_list': [],
            'partial_eo_list': [],
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
            logger.info(f"STARTING ROBUST SCRAPE FOR {stats['total_eos']} EO NUMBERS")
            logger.info(f"Max retries per EO: {MAX_EO_RETRIES}")
            if self.pages_per_eo:
                logger.info(f"Safety limit: {self.pages_per_eo} pages per EO")
            else:
                logger.info(f"No page limit - will scrape all available pages")
            logger.info("=" * 60)

            for idx, eo_number in enumerate(eo_numbers, 1):
                logger.info(f"\n[{idx}/{stats['total_eos']}] Processing EO: {eo_number}")

                # Process EO with retry logic
                result = self.process_eo_with_retries(eo_number)

                status = result['status']
                converters = result['converters']

                # Update stats based on status
                if status == EOStatus.SUCCESS:
                    stats['successful_eos'] += 1
                    stats['total_converters'] += len(converters)
                    stats['successful_eo_list'].append(eo_number)

                    # Save to database
                    created, updated = self._save_converters(converters)
                    stats['created'] += created
                    stats['updated'] += updated

                    logger.info(f"EO {eo_number} | status={EOStatus.SUCCESS} | saved {created} new, {updated} updated")

                elif status == EOStatus.NO_RESULTS:
                    stats['no_results_eos'] += 1
                    stats['no_results_eo_list'].append(eo_number)
                    logger.info(f"EO {eo_number} | status={EOStatus.NO_RESULTS}")

                elif status == EOStatus.PARTIAL:
                    stats['partial_eos'] += 1
                    stats['total_converters'] += len(converters)
                    stats['partial_eo_list'].append(eo_number)

                    # Save partial data
                    created, updated = self._save_converters(converters)
                    stats['created'] += created
                    stats['updated'] += updated

                    logger.warning(f"EO {eo_number} | status={EOStatus.PARTIAL} | saved {created} new, {updated} updated | reason={result.get('error')}")

                else:  # FAILED
                    stats['failed_eos'] += 1
                    stats['failed_eo_list'].append(eo_number)
                    logger.error(f"EO {eo_number} | status={EOStatus.FAILED} | reason={result.get('error')}")

                # Brief pause between EOs
                time.sleep(2)

            # Final statistics
            logger.info("\n" + "=" * 60)
            logger.info("SCRAPING COMPLETE")
            logger.info("=" * 60)
            logger.info(f"Total EOs processed: {stats['total_eos']}")
            logger.info(f"Successful: {stats['successful_eos']}")
            logger.info(f"No results: {stats['no_results_eos']}")
            logger.info(f"Partial: {stats['partial_eos']}")
            logger.info(f"Failed: {stats['failed_eos']}")
            logger.info(f"Total converters found: {stats['total_converters']}")
            logger.info(f"Created: {stats['created']}")
            logger.info(f"Updated: {stats['updated']}")

            if stats['failed_eo_list']:
                logger.info(f"\nFailed EOs ({len(stats['failed_eo_list'])}):")
                for eo in stats['failed_eo_list'][:20]:
                    logger.info(f"  - {eo}")
                if len(stats['failed_eo_list']) > 20:
                    logger.info(f"  ... and {len(stats['failed_eo_list']) - 20} more")

            if stats['partial_eo_list']:
                logger.info(f"\nPartial EOs ({len(stats['partial_eo_list'])}):")
                for eo in stats['partial_eo_list'][:10]:
                    logger.info(f"  - {eo}")
                if len(stats['partial_eo_list']) > 10:
                    logger.info(f"  ... and {len(stats['partial_eo_list']) - 10} more")

        except Exception as e:
            logger.error(f"Critical error during scraping: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._close_driver()

        return stats
