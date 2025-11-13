"""
CARB Website Scraper - Selenium-based scraping for the interactive CARB website
This scraper handles the ASP.NET AJAX website to extract live data
"""

import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

logger = logging.getLogger(__name__)


class CARBWebsiteScraper:
    """Scraper for CARB catalytic converter website using Selenium"""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    def __init__(self, headless=True, timeout=10):
        """
        Initialize the website scraper

        Args:
            headless: Run browser in headless mode (no GUI)
            timeout: Default timeout for element waits in seconds
        """
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def _setup_driver(self):
        """Set up Chrome WebDriver with appropriate options"""
        options = webdriver.ChromeOptions()

        if self.headless:
            options.add_argument('--headless')

        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')

        # Suppress logging
        options.add_argument('--log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(5)
            logger.info("Chrome WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome WebDriver: {e}")
            raise

    def _close_driver(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Chrome WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")

    def scrape_all_data(self, limit_manufacturers=None) -> List[Dict]:
        """
        Scrape all catalytic converter data from the website

        Args:
            limit_manufacturers: Optional limit on number of manufacturers to scrape (for testing)

        Returns:
            List of converter dictionaries
        """
        converters_data = []

        try:
            self._setup_driver()
            self.driver.get(self.BASE_URL)
            logger.info(f"Loaded website: {self.BASE_URL}")

            # Wait for page to load
            time.sleep(3)

            # Get list of manufacturers
            manufacturers = self._get_manufacturers()
            logger.info(f"Found {len(manufacturers)} manufacturers")

            if limit_manufacturers:
                manufacturers = manufacturers[:limit_manufacturers]
                logger.info(f"Limited to {len(manufacturers)} manufacturers for testing")

            # Scrape data for each manufacturer
            for idx, manufacturer in enumerate(manufacturers, 1):
                logger.info(f"[{idx}/{len(manufacturers)}] Scraping manufacturer: {manufacturer}")

                try:
                    manufacturer_data = self._scrape_manufacturer(manufacturer)
                    converters_data.extend(manufacturer_data)
                    logger.info(f"  → Found {len(manufacturer_data)} converters")

                    # Be respectful - add delay between requests
                    time.sleep(2)

                except Exception as e:
                    logger.error(f"  → Error scraping {manufacturer}: {e}")
                    continue

            logger.info(f"Total converters scraped: {len(converters_data)}")

        except Exception as e:
            logger.error(f"Error in scrape_all_data: {e}")
        finally:
            self._close_driver()

        return converters_data

    def _get_manufacturers(self) -> List[str]:
        """Extract list of manufacturers from the page"""
        manufacturers = []

        try:
            # First, click the "Make" dropdown button to reveal manufacturers
            make_button = WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes"))
            )
            logger.info("Found Make dropdown button")
            make_button.click()
            time.sleep(1)  # Wait for dropdown to open

            # Now find all manufacturer links in the dropdown menu
            make_links = self.driver.find_elements(
                By.XPATH,
                "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes')]"
            )

            logger.info(f"Found {len(make_links)} manufacturer links in dropdown")

            for link in make_links:
                text = link.text.strip()
                if text:
                    manufacturers.append(text)

            # Close dropdown by clicking elsewhere
            try:
                self.driver.find_element(By.TAG_NAME, "body").click()
            except:
                pass

        except Exception as e:
            logger.error(f"Error extracting manufacturers: {e}")
            logger.exception(e)

        return manufacturers

    def _scrape_manufacturer(self, manufacturer: str) -> List[Dict]:
        """
        Scrape all converters for a specific manufacturer
        Uses proper ASP.NET postback mechanism for sequential field enabling

        Args:
            manufacturer: Name of the manufacturer

        Returns:
            List of converter dictionaries
        """
        converters = []

        try:
            # Reload page to reset form state
            self.driver.get(self.BASE_URL)
            time.sleep(3)

            # STEP 1: Select Make (manufacturer)
            logger.info(f"Step 1: Selecting Make = {manufacturer}")
            make_button = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes")
            self.driver.execute_script("arguments[0].click();", make_button)
            time.sleep(1)

            # Find manufacturer link and trigger postback
            manufacturer_xpath = f"//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes') and text()='{manufacturer}']"
            make_link = self.driver.find_element(By.XPATH, manufacturer_xpath)

            href = make_link.get_attribute('href')
            import re
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
            if match:
                target = match.group(1)
                argument = match.group(2)
                # Set hidden fields and submit form (bypasses strict mode issues)
                self.driver.execute_script(f"""
                    var theForm = document.forms[0];
                    theForm.__EVENTTARGET.value = '{target}';
                    theForm.__EVENTARGUMENT.value = '{argument}';
                    theForm.submit();
                """)
                logger.info(f"✓ Triggered postback for {manufacturer}")
            else:
                self.driver.execute_script("arguments[0].click();", make_link)
                logger.info(f"✓ Clicked {manufacturer} (fallback)")

            time.sleep(8)  # Wait for ASP.NET postback

            # STEP 2: Get available model years and select one from target range
            logger.info("Step 2: Selecting Model Year from 2010-2020 range")
            year_button = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModelYears")
            self.driver.execute_script("arguments[0].click();", year_button)
            time.sleep(1)

            # Get all available years
            year_links = self.driver.find_elements(
                By.XPATH,
                "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModelYears')]"
            )

            if not year_links:
                logger.warning(f"No model years found for {manufacturer}")
                return converters

            # Try to find a year in the 2010-2020 range (most likely to have data)
            year_link = None
            year_text = None
            target_years = range(2015, 2021)  # 2015-2020 most likely to have converter data

            for target_year in target_years:
                for link in year_links:
                    link_text = link.text.strip()
                    if link_text == str(target_year):
                        year_link = link
                        year_text = link_text
                        logger.info(f"Found target year: {year_text}")
                        break
                if year_link:
                    break

            # If no target year found, use first available
            if not year_link:
                year_link = year_links[0]
                year_text = year_link.text.strip()
                logger.info(f"Using first available year: {year_text}")

            href = year_link.get_attribute('href')
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
            if match:
                target = match.group(1)
                argument = match.group(2)
                self.driver.execute_script(f"""
                    var theForm = document.forms[0];
                    theForm.__EVENTTARGET.value = '{target}';
                    theForm.__EVENTARGUMENT.value = '{argument}';
                    theForm.submit();
                """)
                logger.info(f"✓ Selected year: {year_text}")

            time.sleep(8)  # Wait for postback

            # STEP 3: Select first available Model
            logger.info("Step 3: Selecting first available Model")
            model_button = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModels")
            self.driver.execute_script("arguments[0].click();", model_button)
            time.sleep(1)

            model_links = self.driver.find_elements(
                By.XPATH,
                "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModels')]"
            )

            if not model_links:
                logger.warning(f"No models found for {manufacturer} {year_text}")
                return converters

            model_link = model_links[0]
            model_text = model_link.text.strip()
            self.driver.execute_script("arguments[0].click();", model_link)
            logger.info(f"✓ Selected model: {model_text}")
            time.sleep(5)

            # STEP 4: Always select Engine Size if available (improves result accuracy)
            logger.info("Step 4: Selecting Engine Size if available")

            try:
                # Try to find and click engine size dropdown
                engine_button = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnEngineSizes")
                self.driver.execute_script("arguments[0].click();", engine_button)
                time.sleep(1)

                engine_links = self.driver.find_elements(
                    By.XPATH,
                    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrEngineSizes')]"
                )

                if engine_links:
                    engine_link = engine_links[0]
                    engine_text = engine_link.text.strip()
                    self.driver.execute_script("arguments[0].click();", engine_link)
                    logger.info(f"✓ Selected engine: {engine_text}")
                    time.sleep(5)
                else:
                    logger.info("No engine size options available")
            except Exception as e:
                logger.info(f"Engine size not required or not available: {e}")

            # STEP 5: Click Search Button
            logger.info("Step 5: Clicking Search button")
            search_button = self.driver.find_element(By.ID, "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnVehicleSearch")
            self.driver.execute_script("arguments[0].click();", search_button)
            time.sleep(15)  # Wait for results

            # STEP 6: Extract results with pagination
            converters = self._extract_all_pages(manufacturer)
            logger.info(f"✓ Extracted {len(converters)} converters for {manufacturer}")

        except Exception as e:
            logger.error(f"Error scraping manufacturer {manufacturer}: {e}")
            logger.exception(e)

        return converters

    def _extract_all_pages(self, manufacturer: str) -> List[Dict]:
        """
        Extract results from all paginated pages

        Args:
            manufacturer: Name of the manufacturer

        Returns:
            List of all converter dictionaries across all pages
        """
        all_converters = []
        page_num = 1

        while True:
            logger.info(f"Extracting page {page_num}...")

            # Extract current page
            page_converters = self._extract_results_data(manufacturer)

            if not page_converters:
                logger.info("No results found on this page")
                break

            all_converters.extend(page_converters)
            logger.info(f"  → Page {page_num}: {len(page_converters)} converters")

            # Check for "Next" pagination button
            try:
                # Look for pagination "Next" button or next page link
                # ASP.NET GridView pagination typically uses table structure
                next_button = None

                # Try finding "Next" or ">" link in pagination
                try:
                    next_button = self.driver.find_element(
                        By.XPATH,
                        "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']//tr//td//a[contains(text(), '>')]"
                    )
                except:
                    pass

                # Try alternative pagination patterns
                if not next_button:
                    try:
                        # Look for numbered page links (current page + 1)
                        next_page_num = page_num + 1
                        next_button = self.driver.find_element(
                            By.XPATH,
                            f"//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']//tr//td//a[text()='{next_page_num}']"
                        )
                    except:
                        pass

                # Try ASP.NET postback pattern for pagination
                if not next_button:
                    try:
                        next_button = self.driver.find_element(
                            By.XPATH,
                            "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']//tr//td//a[contains(@href, 'Page$Next')]"
                        )
                    except:
                        pass

                if next_button:
                    # Check if button is enabled (not disabled/grayed out)
                    button_classes = next_button.get_attribute("class") or ""
                    if "disabled" not in button_classes.lower():
                        logger.info(f"Found next page button, navigating to page {page_num + 1}...")

                        # Use JavaScript click to avoid interception
                        self.driver.execute_script("arguments[0].click();", next_button)
                        time.sleep(5)  # Wait for next page to load
                        page_num += 1
                        continue
                    else:
                        logger.info("Next button is disabled - reached last page")
                        break
                else:
                    logger.info("No next page button found - single page of results")
                    break

            except Exception as e:
                logger.debug(f"Pagination ended: {e}")
                break

        logger.info(f"Total across all pages: {len(all_converters)} converters from {page_num} page(s)")
        return all_converters

    def _extract_results_data(self, manufacturer: str) -> List[Dict]:
        """
        Extract converter data from the results table

        Table structure:
        [0] Test Group Name
        [1] Application Type
        [2] Part Manufacturer
        [3] Manufacturer Part Number
        [4] Cert Level
        [5] Executive Order
        [6] Vehicle Class
        [7] Total Converters
        [8] Catalyst Location
        [9] Catalyst Part Type

        Args:
            manufacturer: Name of the manufacturer

        Returns:
            List of converter dictionaries
        """
        converters = []

        try:
            # Wait for results table to appear
            table = WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((
                    By.ID,
                    "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData"
                ))
            )

            # Find all data rows (skip header row)
            rows = table.find_elements(By.XPATH, ".//tr[td[@class='veh']]")
            logger.info(f"Found {len(rows)} result rows")

            for row in rows:
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")

                    if len(cells) >= 10:  # Ensure we have all expected columns
                        # Extract EO number from link
                        eo_cell = cells[5]
                        eo_link = eo_cell.find_element(By.TAG_NAME, "a")
                        eo_number = eo_link.text.strip()

                        converter = {
                            'manufacturer_name': cells[2].text.strip(),  # Part Manufacturer
                            'executive_order': eo_number,  # Executive Order
                            'part_number': cells[3].text.strip(),  # Manufacturer Part Number
                            'test_group': cells[0].text.strip(),  # Test Group Name
                            'application_type': cells[1].text.strip(),  # Application Type
                            'cert_level': cells[4].text.strip(),  # Cert Level
                            'vehicle_class': cells[6].text.strip(),  # Vehicle Class
                            'total_converters': cells[7].text.strip(),  # Total Converters
                            'catalyst_location': cells[8].text.strip(),  # Catalyst Location
                            'part_type': cells[9].text.strip(),  # Catalyst Part Type
                            'scraped_at': datetime.now(),
                        }

                        converters.append(converter)

                except Exception as e:
                    logger.debug(f"Error parsing row: {e}")
                    continue

        except TimeoutException:
            logger.warning("No results table found or timeout waiting for table")
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            logger.exception(e)

        return converters

    def _parse_year_range(self, year_str: str) -> tuple:
        """
        Parse year range string into start and end years

        Args:
            year_str: Year string like "2010-2015" or "2010"

        Returns:
            Tuple of (start_year, end_year)
        """
        import re

        if not year_str:
            return None, None

        # Remove any non-digit and non-dash characters
        year_str = re.sub(r'[^\d-]', '', year_str)

        if '-' in year_str:
            parts = year_str.split('-')
            try:
                return int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                return None, None
        else:
            try:
                year = int(year_str)
                return year, year
            except ValueError:
                return None, None

    def _parse_vehicle_info(self, vehicle_info: str) -> Dict:
        """
        Parse vehicle information to extract make, model, and class

        Args:
            vehicle_info: Vehicle information string

        Returns:
            Dictionary with make, model, vehicle_class
        """
        import re

        result = {
            'make': None,
            'model': None,
            'vehicle_class': vehicle_info,
            'engine_size': None,
        }

        if not vehicle_info:
            return result

        # Common vehicle makes
        common_makes = [
            'Ford', 'Honda', 'Toyota', 'Chevrolet', 'Chevy', 'GM', 'Chrysler',
            'Nissan', 'BMW', 'Mazda', 'Dodge', 'Jeep', 'Subaru', 'Volkswagen',
            'VW', 'Audi', 'Mercedes', 'Mercedes-Benz', 'Lexus', 'Acura',
            'Infiniti', 'Hyundai', 'Kia', 'Mitsubishi', 'Volvo', 'Porsche',
            'Jaguar', 'Land Rover', 'Mini', 'Buick', 'Cadillac', 'GMC',
            'Lincoln', 'Ram', 'Saab', 'Saturn', 'Suzuki', 'Isuzu'
        ]

        # Extract make
        for make in common_makes:
            pattern = r'\b' + re.escape(make) + r'\b'
            if re.search(pattern, vehicle_info, re.IGNORECASE):
                result['make'] = make
                break

        # Extract engine size (e.g., "1.6L", "2.9L")
        engine_match = re.search(r'(\d+\.?\d*)\s*[Ll]', vehicle_info)
        if engine_match:
            result['engine_size'] = engine_match.group(1)

        return result

    def scrape_by_eo_number(self, eo_number: str) -> Optional[Dict]:
        """
        Scrape data for a specific Executive Order number

        Args:
            eo_number: Executive Order number (e.g., "D-193-143")

        Returns:
            Converter dictionary or None if not found
        """
        try:
            self._setup_driver()
            self.driver.get(self.BASE_URL)
            logger.info(f"Searching for EO: {eo_number}")

            # Wait for page to load
            time.sleep(2)

            # Find and use EO search
            # This will depend on the actual website structure
            # You may need to adjust selectors

            # Example: Find EO input and search
            eo_input = self.driver.find_element(By.ID, "eo_input_id")  # Adjust ID
            eo_input.clear()
            eo_input.send_keys(eo_number)

            search_btn = self.driver.find_element(By.ID, "search_button_id")  # Adjust ID
            search_btn.click()

            time.sleep(2)

            # Extract result
            converters = self._extract_results_data("Unknown")

            return converters[0] if converters else None

        except Exception as e:
            logger.error(f"Error searching for EO {eo_number}: {e}")
            return None
        finally:
            self._close_driver()


def test_website_scraper(limit=2):
    """Test the website scraper with a limited number of manufacturers"""
    logger.info("Testing CARB Website Scraper")

    scraper = CARBWebsiteScraper(headless=False)  # Set False to see browser

    try:
        converters = scraper.scrape_all_data(limit_manufacturers=limit)
        logger.info(f"\nScraped {len(converters)} total converters")

        if converters:
            logger.info("\nSample data:")
            for conv in converters[:3]:
                logger.info(f"  - {conv.get('manufacturer_name')}: {conv.get('executive_order')}")

        return converters

    except Exception as e:
        logger.error(f"Test failed: {e}")
        return []


if __name__ == "__main__":
    # Set up logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run test
    test_website_scraper(limit=2)
