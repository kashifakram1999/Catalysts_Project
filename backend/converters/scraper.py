"""
CARB Catalytic Converter Data Scraper
Extracts data from CARB website and PDF sources
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CARBScraper:
    """Scraper for CARB catalytic converter data"""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
    PDF_URL = "https://ww2.arb.ca.gov/sites/default/files/aftermarket/aftermktcat/exemptcat09.pdf"
    LOCAL_PDF = "/Users/muhmmadkashif/Desktop/Data.pdf"

    def __init__(self, use_local=True):
        self.use_local = use_local
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })

    def scrape_website(self) -> List[Dict]:
        """
        Scrape data from the CARB website
        This is a complex ASP.NET site with AJAX, so we'll need Selenium
        """
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait, Select
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException

        logger.info("Starting website scraping...")
        converters_data = []

        try:
            # Set up headless Chrome
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')

            driver = webdriver.Chrome(options=options)
            driver.get(self.BASE_URL)

            time.sleep(3)  # Wait for page load

            # Try to get the list of makes
            try:
                # Find the makes list
                makes_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='__doPostBack']")
                makes = []

                for elem in makes_elements:
                    text = elem.text.strip()
                    if text and len(text) > 1:
                        makes.append(text)

                logger.info(f"Found {len(makes)} vehicle makes")

                # For demonstration, we'll scrape a subset
                # In production, you'd scrape all makes
                for make in makes[:5]:  # Limit to first 5 for demo
                    logger.info(f"Scraping data for {make}...")
                    # Click on the make
                    # This would require more complex interaction with ASP.NET postbacks
                    # For now, we'll note this needs further development

            except Exception as e:
                logger.error(f"Error finding makes: {e}")

            driver.quit()

        except Exception as e:
            logger.error(f"Error in website scraping: {e}")

        return converters_data

    def scrape_pdf(self) -> List[Dict]:
        """
        Download and parse the CARB PDF for converter data
        """
        import PyPDF2
        import io
        import os

        converters_data = []

        try:
            if self.use_local and os.path.exists(self.LOCAL_PDF):
                logger.info(f"Reading local PDF from {self.LOCAL_PDF}...")
                with open(self.LOCAL_PDF, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    logger.info(f"PDF has {len(pdf_reader.pages)} pages")

                    all_text = ""
                    for page in pdf_reader.pages:
                        all_text += page.extract_text() + "\n"
            else:
                logger.info("Downloading CARB PDF from remote URL...")
                response = self.session.get(self.PDF_URL, timeout=30)
                response.raise_for_status()

                # Read PDF
                pdf_file = io.BytesIO(response.content)
                pdf_reader = PyPDF2.PdfReader(pdf_file)

                logger.info(f"PDF has {len(pdf_reader.pages)} pages")

                all_text = ""
                for page in pdf_reader.pages:
                    all_text += page.extract_text() + "\n"

            # Parse the text to extract converter data
            converters_data = self._parse_pdf_text(all_text)
            logger.info(f"Extracted {len(converters_data)} records from PDF")

        except Exception as e:
            logger.error(f"Error downloading/parsing PDF: {e}")

        return converters_data

    def _parse_pdf_text(self, text: str) -> List[Dict]:
        """
        Parse PDF text to extract converter information from CARB PDF format
        Format: EO/Date | Series/Model | Model Year | Make/Class
        """
        converters = []
        lines = text.split('\n')

        current_manufacturer = None
        current_manufacturer_contact = None
        i = 0

        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and headers
            if not line or 'Page' in line or 'Vehicle Application' in line or 'EO/Date' in line or 'Series/Model' in line or 'Model Year' in line or 'Make/Class' in line or 'view document' in line or 'Click on highlighted' in line:
                i += 1
                continue

            # Check for phone number line - indicates manufacturer section
            # Handle various phone formats: (XXX) XXX-XXXX, (XXX) XXX -XXXX, (XXX) XXX- XXXX
            phone_match = re.search(r'\(\d{3}\)\s*\d{3}\s*-?\s*\d{4}', line)
            if phone_match:
                # Extract the phone number
                current_manufacturer_contact = phone_match.group(0)
                # Normalize phone format - remove spaces around dash and extra spaces
                current_manufacturer_contact = re.sub(r'\s*-\s*', '-', current_manufacturer_contact)
                current_manufacturer_contact = re.sub(r'\s+', ' ', current_manufacturer_contact)

                # Look back for company name (usually 2-4 lines before phone)
                manufacturer_parts = []
                for j in range(max(0, i-4), i):
                    prev_line = lines[j].strip()
                    # Skip headers and empty lines
                    if not prev_line or 'Page' in prev_line or 'Application' in prev_line:
                        continue
                    # Skip header columns specifically
                    if prev_line in ['Company', 'EO/Date', 'Series/Model', 'Model Year', 'Make/Class']:
                        continue
                    # Skip lines that are only numbers or very short
                    if len(prev_line) <= 2 or prev_line.isdigit():
                        continue
                    # Skip alert lines
                    if 'Alert' in prev_line or 'document' in prev_line or 'Click on' in prev_line:
                        continue
                    # Skip "See" inspection lines
                    if prev_line.startswith('*') and 'See' in prev_line:
                        continue
                    # Skip EO lines (they start with D-XXX-XX or *D-XXX-XX)
                    if re.match(r'^\*?D-\d+-\d+', prev_line):
                        continue
                    # Add company name parts (including Company, Inc., etc.)
                    manufacturer_parts.append(prev_line)

                if manufacturer_parts:
                    # Join all parts and clean up
                    current_manufacturer = ' '.join(manufacturer_parts)
                    # Remove extra whitespace
                    current_manufacturer = ' '.join(current_manufacturer.split())
                    # Clean up common formatting issues from PDF extraction
                    current_manufacturer = current_manufacturer.replace('M anufacturing', 'Manufacturing')
                    logger.info(f"Found manufacturer: {current_manufacturer} - Contact: {current_manufacturer_contact}")
                i += 1
                continue

            # Look for Executive Order pattern (D-XXX-XX/MM-DD-YY format)
            eo_match = re.search(r'(\*?D-\d+-\d+)/(\d{2}-\d{2}-\d{2}|\d{2}-\d{2}-\d{4})', line)

            if eo_match and current_manufacturer:
                try:
                    eo_number = eo_match.group(1).replace('*', '')
                    eo_date_str = eo_match.group(2)

                    # Parse the rest of the line after EO
                    rest_of_line = line[eo_match.end():].strip()

                    # Extract Series/Model (alphanumeric codes/text before year)
                    series_model = None
                    # Match alphanumeric characters, dashes, slashes, spaces until we hit a year or end
                    series_match = re.search(r'^\s*([A-Za-z0-9\-/\s]+?)(?=\s+(?:19|20)\d{2}|$)', rest_of_line)
                    if series_match:
                        series_model = series_match.group(1).strip()
                        rest_of_line = rest_of_line[series_match.end():].strip()

                    # Extract Year range (YYYY - YYYY or YYYY & older or single YYYY)
                    model_year_start = None
                    model_year_end = None

                    # Pattern: "YYYY - YYYY" or "YYYY – YYYY" (with various dashes and spaces)
                    year_range_match = re.search(r'(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}', rest_of_line)
                    if year_range_match:
                        years = re.findall(r'(?:19|20)\d{2}', year_range_match.group(0))
                        model_year_start = int(years[0])
                        model_year_end = int(years[1])
                        rest_of_line = rest_of_line[year_range_match.end():].strip()
                    else:
                        # Pattern: "YYYY & older"
                        older_match = re.search(r'(?:19|20)\d{2}\s*&\s*older', rest_of_line)
                        if older_match:
                            year = re.search(r'(?:19|20)\d{2}', older_match.group(0)).group(0)
                            model_year_start = 1975  # Assume oldest year
                            model_year_end = int(year)
                            rest_of_line = rest_of_line[older_match.end():].strip()
                        else:
                            # Pattern: single "YYYY" (check if part of range or standalone)
                            single_year_match = re.search(r'(?:19|20)\d{2}', rest_of_line)
                            if single_year_match:
                                year = int(single_year_match.group(0))
                                # Check if there's another year after dash
                                next_year_match = re.search(r'[-–]\s*(?:19|20)\d{2}', rest_of_line[single_year_match.end():])
                                if next_year_match:
                                    model_year_start = year
                                    model_year_end = int(re.search(r'(?:19|20)\d{2}', next_year_match.group(0)).group(0))
                                    rest_of_line = rest_of_line[single_year_match.end() + next_year_match.end():].strip()
                                else:
                                    model_year_start = year
                                    model_year_end = year
                                    rest_of_line = rest_of_line[single_year_match.end():].strip()

                    # Extract Make/Class (everything remaining)
                    make_class = rest_of_line.strip()

                    # Try to separate make from class
                    make = None
                    model = None
                    engine_size = None
                    vehicle_class = make_class

                    # Comprehensive list of vehicle makes
                    common_makes = [
                        'Ford', 'Honda', 'Toyota', 'Chevrolet', 'Chevy', 'GM', 'Chrysler',
                        'Nissan', 'BMW', 'Mazda', 'Dodge', 'Jeep', 'Subaru', 'Volkswagen',
                        'VW', 'Audi', 'Mercedes', 'Mercedes-Benz', 'Lexus', 'Acura',
                        'Infiniti', 'Hyundai', 'Kia', 'Mitsubishi', 'Volvo', 'Porsche',
                        'Jaguar', 'Land Rover', 'Mini', 'Buick', 'Cadillac', 'GMC',
                        'Lincoln', 'Ram', 'Saab', 'Saturn', 'Suzuki', 'Isuzu'
                    ]

                    # Extract engine size if present (e.g., "1.6L", "2.9L", "3.5L")
                    engine_match = re.search(r'(\d+\.?\d*)\s*[Ll]', make_class)
                    if engine_match:
                        engine_size = engine_match.group(1)
                        make_class = make_class.replace(engine_match.group(0), '').strip()
                        logger.debug(f"Extracted engine size: {engine_size} from '{make_class}'")

                    # Try to extract make - check if make appears at start or in the string
                    for common_make in common_makes:
                        # Case insensitive search with word boundary
                        pattern = r'\b' + re.escape(common_make) + r'\b'
                        if re.search(pattern, make_class, re.IGNORECASE):
                            make = common_make
                            # Remove make from the string to get remaining class/model info
                            vehicle_class = re.sub(pattern, '', make_class, flags=re.IGNORECASE).strip()
                            # Clean up extra slashes and spaces
                            vehicle_class = re.sub(r'\s*/\s*', '/', vehicle_class)
                            vehicle_class = re.sub(r'^/|/$', '', vehicle_class).strip()
                            break

                    # Try to extract model name (common models)
                    common_models = ['Civic', 'Civics', 'Accord', 'Camry', 'Corolla', 'F-150', 'Silverado', 'Altima']
                    for common_model in common_models:
                        if re.search(r'\b' + re.escape(common_model) + r'\b', make_class, re.IGNORECASE):
                            model = common_model
                            break

                    # Parse EO date
                    try:
                        eo_date = datetime.strptime(eo_date_str, '%m-%d-%y').date()
                    except:
                        try:
                            eo_date = datetime.strptime(eo_date_str, '%m-%d-%Y').date()
                        except:
                            eo_date = None

                    # Create converter record
                    converter = {
                        'manufacturer_name': current_manufacturer,
                        'manufacturer_contact': current_manufacturer_contact,
                        'executive_order': eo_number,
                        'series_model': series_model,
                        'model_year_start': model_year_start,
                        'model_year_end': model_year_end,
                        'make': make,
                        'model': model,
                        'vehicle_class': vehicle_class,
                        'engine_size': engine_size,
                        'eo_date': eo_date,
                    }

                    converters.append(converter)
                    logger.debug(f"Parsed: {eo_number} - {make} {model_year_start}-{model_year_end}")

                except Exception as e:
                    logger.error(f"Error parsing line: {line}, Error: {e}")

            i += 1

        logger.info(f"Total converters parsed: {len(converters)}")
        return converters

    def parse_year_range(self, year_str: str) -> tuple:
        """Parse year string to start and end year"""
        if '-' in year_str:
            parts = year_str.split('-')
            return int(parts[0].strip()), int(parts[1].strip())
        else:
            year = int(year_str.strip())
            return year, year

    def extract_make_model(self, text: str) -> Dict:
        """Extract make and model from text"""
        # Common makes
        makes = [
            'Honda', 'Toyota', 'Ford', 'Chevrolet', 'Nissan', 'BMW', 'Mercedes',
            'Volkswagen', 'Audi', 'Mazda', 'Subaru', 'Hyundai', 'Kia', 'Jeep',
            'Ram', 'GMC', 'Dodge', 'Chrysler', 'Lexus', 'Acura', 'Infiniti'
        ]

        result = {'make': None, 'model': None}

        for make in makes:
            if make.lower() in text.lower():
                result['make'] = make
                # Try to extract model (word after make)
                pattern = f'{make}\\s+(\\w+)'
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    result['model'] = match.group(1)
                break

        return result

    def delay(self, seconds: int = 2):
        """Add delay to be respectful to the server"""
        time.sleep(seconds)


class CARBDataProcessor:
    """Process and clean scraped CARB data"""

    @staticmethod
    def clean_converter_data(raw_data: Dict) -> Dict:
        """Clean and normalize converter data"""
        cleaned = {}

        # Clean executive order
        if 'executive_order' in raw_data:
            cleaned['executive_order'] = raw_data['executive_order'].strip()

        # Clean years
        for field in ['model_year_start', 'model_year_end']:
            if field in raw_data:
                try:
                    cleaned[field] = int(raw_data[field])
                except (ValueError, TypeError):
                    pass

        # Clean text fields
        text_fields = ['make', 'model', 'product_name', 'manufacturer_name', 'manufacturer_contact',
                      'vehicle_class', 'test_group', 'cert_level', 'series_model', 'engine_size']
        for field in text_fields:
            if field in raw_data and raw_data[field]:
                cleaned[field] = str(raw_data[field]).strip()

        # Clean date field
        if 'eo_date' in raw_data and raw_data['eo_date']:
            cleaned['eo_date'] = raw_data['eo_date']

        return cleaned

    @staticmethod
    def validate_converter_data(data: Dict) -> bool:
        """Validate that converter data has required fields"""
        required_fields = ['executive_order']
        return all(field in data for field in required_fields)
