#!/usr/bin/env python3
"""
Test_Car_Records
================

Utility script that inspects the first vehicle make available on the CARB
Vehicle Search tab and iterates through every dependent year / model / engine
combination. Each combination is submitted and the number of rows shown in the
results grid is counted. Totals and per-combination counts are printed to stdout.

Usage:
    python backend/converters/Test_Car_Records.py --workers 4 --show-browser
"""

from __future__ import annotations

import argparse
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


LOGGER = logging.getLogger("Test_Car_Records")

# Page constants
BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
MAKE_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnMakes"
YEAR_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModelYears"
MODEL_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnModels"
ENGINE_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnEngineSizes"
SEARCH_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_btnVehicleSearch"
RESULTS_TABLE_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData"

MAKE_OPTION_XPATH = (
    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrMakes')]"
)
YEAR_OPTION_XPATH = (
    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModelYears')]"
)
MODEL_OPTION_XPATH = (
    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrModels')]"
)
ENGINE_OPTION_XPATH = (
    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrEngineSizes')]"
)


@dataclass
class VehicleQuery:
    """Filter combination to submit on the Vehicle Search form."""

    year: str
    model: str
    engine: Optional[str]


@dataclass
class QueryResult(VehicleQuery):
    """Result for a submitted VehicleQuery."""

    record_count: int
    worker: str


class DropdownSelectionError(Exception):
    """Raised when a dropdown option cannot be selected."""


class TestCarRecordsRunner:
    """
    Coordinates dropdown inspection and record counting for the Vehicle Search tab.
    """

    def __init__(self, *, headless: bool = True, timeout: int = 25, workers: int = 1):
        self.headless = headless
        self.timeout = timeout
        self.workers = max(1, workers)
        self.first_make: Optional[str] = None
        self._driver: Optional[webdriver.Chrome] = None
        # Lock used when logging from worker threads
        self._log_lock = threading.Lock()

    # ------------------------------------------------------------------ Driver
    def _create_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(90)
        driver.implicitly_wait(2)
        return driver

    def _ensure_driver(self) -> webdriver.Chrome:
        if not self._driver:
            self._driver = self._create_driver()
        return self._driver

    def _close_main_driver(self) -> None:
        if self._driver:
            try:
                self._driver.quit()
            except WebDriverException:
                pass
            self._driver = None

    # ------------------------------------------------------------ Core driver
    def _wait_for_ready_state(self, driver: webdriver.Chrome, *, delay: float = 1.0) -> None:
        """
        Wait for document readyState and give the ASP.NET UpdatePanel time to settle.
        """
        try:
            WebDriverWait(driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            LOGGER.debug("Document readyState timeout ignored")
        time.sleep(delay)

    def _dismiss_menu(self, driver: webdriver.Chrome) -> None:
        driver.execute_script("document.body.click();")
        time.sleep(0.2)

    def _parse_postback(self, href: str) -> Optional[Tuple[str, str]]:
        if not href:
            return None
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if not match:
            return None
        return match.group(1), match.group(2)

    def _execute_postback(self, driver: webdriver.Chrome, *, target: str, argument: str) -> None:
        target = target.replace("'", "\\'")
        argument = argument.replace("'", "\\'")
        driver.execute_script(
            """
            var theForm = document.forms[0];
            if (!theForm.__EVENTTARGET) {
                var targetInput = document.createElement('input');
                targetInput.type = 'hidden';
                targetInput.name = '__EVENTTARGET';
                theForm.appendChild(targetInput);
            }
            if (!theForm.__EVENTARGUMENT) {
                var argInput = document.createElement('input');
                argInput.type = 'hidden';
                argInput.name = '__EVENTARGUMENT';
                theForm.appendChild(argInput);
            }
            theForm.__EVENTTARGET.value = arguments[0];
            theForm.__EVENTARGUMENT.value = arguments[1];
            theForm.submit();
            """,
            target,
            argument,
        )

    def _select_dropdown_option(
        self,
        driver: webdriver.Chrome,
        *,
        button_id: str,
        options_xpath: str,
        value: str,
        wait_description: str,
        post_select_wait: float = 1.5,
    ) -> None:
        button = WebDriverWait(driver, self.timeout).until(
            EC.element_to_be_clickable((By.ID, button_id))
        )
        driver.execute_script("arguments[0].click();", button)
        try:
            options = WebDriverWait(driver, self.timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, options_xpath))
            )
        except TimeoutException as exc:
            self._dismiss_menu(driver)
            raise DropdownSelectionError(f"No options available for {wait_description}") from exc

        target = None
        search_value = value.strip().lower()
        for option in options:
            label = option.text.strip()
            if not label:
                continue
            if label.lower() == search_value:
                target = option
                break

        if not target:
            self._dismiss_menu(driver)
            raise DropdownSelectionError(f"Value '{value}' missing in {wait_description}")

        href = target.get_attribute("href") or ""
        postback = self._parse_postback(href)
        if postback:
            self._execute_postback(driver, target=postback[0], argument=postback[1])
        else:
            driver.execute_script("arguments[0].click();", target)

        self._wait_for_ready_state(driver, delay=post_select_wait)

    def _collect_dropdown_labels(
        self,
        driver: webdriver.Chrome,
        *,
        button_id: str,
        options_xpath: str,
        description: str,
    ) -> List[str]:
        try:
            button = WebDriverWait(driver, self.timeout).until(
                EC.element_to_be_clickable((By.ID, button_id))
            )
        except TimeoutException:
            LOGGER.debug("Dropdown button %s never became clickable", description)
            return []

        driver.execute_script("arguments[0].click();", button)
        try:
            options = WebDriverWait(driver, self.timeout).until(
                EC.presence_of_all_elements_located((By.XPATH, options_xpath))
            )
        except TimeoutException:
            self._dismiss_menu(driver)
            LOGGER.warning("Timed out while opening %s dropdown", description)
            return []

        labels = []
        for option in options:
            text = option.text.strip()
            if text and text not in labels:
                labels.append(text)

        self._dismiss_menu(driver)
        return labels

    # --------------------------------------------------------------- Data prep
    def _prepare_make_and_years(self) -> List[str]:
        driver = self._ensure_driver()
        driver.get(BASE_URL)
        self._wait_for_ready_state(driver, delay=2)

        makes = self._collect_dropdown_labels(
            driver,
            button_id=MAKE_BUTTON_ID,
            options_xpath=MAKE_OPTION_XPATH,
            description="vehicle make",
        )
        usable_makes = [make for make in makes if make]
        if not usable_makes:
            raise RuntimeError("No vehicle makes found on Vehicle Search tab.")

        self.first_make = usable_makes[0]
        LOGGER.info("First vehicle make discovered: %s", self.first_make)
        self._select_dropdown_option(
            driver,
            button_id=MAKE_BUTTON_ID,
            options_xpath=MAKE_OPTION_XPATH,
            value=self.first_make,
            wait_description="vehicle make",
            post_select_wait=2.0,
        )

        year_labels = self._collect_dropdown_labels(
            driver,
            button_id=YEAR_BUTTON_ID,
            options_xpath=YEAR_OPTION_XPATH,
            description="model year",
        )
        if not year_labels:
            raise RuntimeError("Model year options did not populate after selecting make.")

        LOGGER.info("Found %d model years for %s", len(year_labels), self.first_make)
        return year_labels

    # -------------------------------------------------------------- Processing
    def _run_worker(self, worker_name: str, years: Sequence[str]) -> List[QueryResult]:
        results: List[QueryResult] = []
        if not years:
            return results

        driver = self._create_driver()
        try:
            driver.get(BASE_URL)
            self._wait_for_ready_state(driver, delay=2)

            for year in years:
                try:
                    self._prepare_year_context(driver)
                    year_results = self._process_year(driver, worker_name, year)
                    results.extend(year_results)
                except Exception as exc:  # pylint: disable=broad-except
                    with self._log_lock:
                        LOGGER.error(
                            "[%s] Failed to process year %s: %s",
                            worker_name,
                            year,
                            exc,
                        )

        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass

        return results

    def _prepare_year_context(self, driver: webdriver.Chrome) -> None:
        driver.get(BASE_URL)
        self._wait_for_ready_state(driver, delay=2)
        self._select_dropdown_option(
            driver,
            button_id=MAKE_BUTTON_ID,
            options_xpath=MAKE_OPTION_XPATH,
            value=self.first_make or "",
            wait_description="vehicle make",
            post_select_wait=2.0,
        )

    def _process_year(self, driver: webdriver.Chrome, worker_name: str, year: str) -> List[QueryResult]:
        year_results: List[QueryResult] = []
        models = self._gather_models_for_year(driver, year)
        if not models:
            LOGGER.info("[%s] No models available for year %s", worker_name, year)
            return year_results

        for model in models:
            engine_labels = self._gather_engines_for_model(driver, year, model)
            if not engine_labels:
                result = self._run_single_query(
                    driver,
                    worker_name,
                    VehicleQuery(year=year, model=model, engine=None),
                )
                if result:
                    year_results.append(result)
                continue

            for engine in engine_labels:
                result = self._run_single_query(
                    driver,
                    worker_name,
                    VehicleQuery(year=year, model=model, engine=engine),
                )
                if result:
                    year_results.append(result)

        return year_results

    def _gather_models_for_year(self, driver: webdriver.Chrome, year: str) -> List[str]:
        for attempt in range(3):
            try:
                self._select_dropdown_option(
                    driver,
                    button_id=YEAR_BUTTON_ID,
                    options_xpath=YEAR_OPTION_XPATH,
                    value=year,
                    wait_description=f"model year {year}",
                )
                time.sleep(0.8)
            except DropdownSelectionError as exc:
                LOGGER.error("Unable to select year %s: %s", year, exc)
                return []

            models = self._collect_dropdown_labels(
                driver,
                button_id=MODEL_BUTTON_ID,
                options_xpath=MODEL_OPTION_XPATH,
                description=f"models for {year}",
            )
            if models:
                return models
            time.sleep(0.5)

        LOGGER.info("No models available after retries for year %s", year)
        return []

    def _gather_engines_for_model(self, driver: webdriver.Chrome, year: str, model: str) -> List[str]:
        for attempt in range(3):
            try:
                self._select_dropdown_option(
                    driver,
                    button_id=YEAR_BUTTON_ID,
                    options_xpath=YEAR_OPTION_XPATH,
                    value=year,
                    wait_description=f"model year {year}",
                )
                self._select_dropdown_option(
                    driver,
                    button_id=MODEL_BUTTON_ID,
                    options_xpath=MODEL_OPTION_XPATH,
                    value=model,
                    wait_description=f"model {model}",
                )
            except DropdownSelectionError as exc:
                LOGGER.error("Failed selecting %s/%s: %s", year, model, exc)
                return []

            engine_labels = self._collect_dropdown_labels(
                driver,
                button_id=ENGINE_BUTTON_ID,
                options_xpath=ENGINE_OPTION_XPATH,
                description=f"engine sizes for {model}",
            )
            if engine_labels:
                return engine_labels
            time.sleep(0.5)

        LOGGER.info("No engine sizes available for %s %s", year, model)
        return []

    def _run_single_query(
        self,
        driver: webdriver.Chrome,
        worker_name: str,
        query: VehicleQuery,
    ) -> Optional[QueryResult]:
        engine_label = query.engine or "ALL ENGINES"
        with self._log_lock:
            LOGGER.info(
                "[%s] Running Year %s | Model %s | Engine %s",
                worker_name,
                query.year,
                query.model,
                engine_label,
            )

        try:
            records = self._execute_query(driver, query)
        except DropdownSelectionError as exc:
            with self._log_lock:
                LOGGER.info(
                    "[%s] Skipping Year %s | Model %s | Engine %s (%s)",
                    worker_name,
                    query.year,
                    query.model,
                    engine_label,
                    exc,
                )
            return None

        with self._log_lock:
            LOGGER.info(
                "[%s] Completed Year %s | Model %s | Engine %s => %d record(s)",
                worker_name,
                query.year,
                query.model,
                engine_label,
                records,
            )

        return QueryResult(
            year=query.year,
            model=query.model,
            engine=query.engine,
            record_count=records,
            worker=worker_name,
        )

    def _execute_query(self, driver: webdriver.Chrome, query: VehicleQuery) -> int:
        self._select_dropdown_option(
            driver,
            button_id=YEAR_BUTTON_ID,
            options_xpath=YEAR_OPTION_XPATH,
            value=query.year,
            wait_description=f"model year {query.year}",
        )
        self._select_dropdown_option(
            driver,
            button_id=MODEL_BUTTON_ID,
            options_xpath=MODEL_OPTION_XPATH,
            value=query.model,
            wait_description=f"model {query.model}",
        )
        if query.engine:
            self._select_dropdown_option(
                driver,
                button_id=ENGINE_BUTTON_ID,
                options_xpath=ENGINE_OPTION_XPATH,
                value=query.engine,
                wait_description=f"engine {query.engine}",
                post_select_wait=1.2,
            )

        search_button = WebDriverWait(driver, self.timeout).until(
            EC.element_to_be_clickable((By.ID, SEARCH_BUTTON_ID))
        )
        driver.execute_script("arguments[0].click();", search_button)
        self._wait_for_ready_state(driver, delay=2.0)

        return self._count_result_rows(driver)

    def _count_result_rows(self, driver: webdriver.Chrome) -> int:
        """
        Count record rows in the results table, following pagination until the end.
        """
        def table_present(drv: webdriver.Chrome) -> bool:
            try:
                drv.find_element(By.ID, RESULTS_TABLE_ID)
                return True
            except NoSuchElementException:
                return False

        def no_data_present(drv: webdriver.Chrome) -> bool:
            try:
                message = drv.find_element(
                    By.XPATH,
                    "//span[contains(@id, 'lblVehicle') and contains(translate(text(),'NO','no'), 'no')]",
                )
                return bool(message.text.strip())
            except NoSuchElementException:
                return False

        try:
            WebDriverWait(driver, self.timeout).until(
                lambda d: table_present(d) or no_data_present(d)
            )
        except TimeoutException:
            LOGGER.warning("Timed out waiting for results table - assuming 0 records")
            return 0

        if no_data_present(driver):
            return 0

        total_rows = 0
        current_page = 1

        while True:
            try:
                table = driver.find_element(By.ID, RESULTS_TABLE_ID)
            except NoSuchElementException:
                break

            rows = table.find_elements(By.XPATH, ".//tr[td[contains(@class,'veh')]]")
            total_rows += len(rows)

            next_link = self._locate_pagination_link(driver, current_page)
            if not next_link:
                break

            driver.execute_script("arguments[0].click();", next_link)
            self._wait_for_ready_state(driver, delay=1.5)
            current_page += 1

        return total_rows

    def _locate_pagination_link(self, driver: webdriver.Chrome, current_page: int):
        try:
            next_button = driver.find_element(
                By.XPATH,
                "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']"
                "//tr//td//a[contains(@href, 'Page$Next')]",
            )
            classes = (next_button.get_attribute("class") or "").lower()
            if next_button.is_enabled() and "disabled" not in classes:
                return next_button
        except NoSuchElementException:
            next_button = None

        possible_selectors = [
            "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']"
            "//tr//td//a[contains(text(), '>')]",
            f"//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCVehicleSearch_gvVehicleData']"
            f"//tr//td//a[text()='{current_page + 1}']",
        ]
        for selector in possible_selectors:
            try:
                elem = driver.find_element(By.XPATH, selector)
                classes = (elem.get_attribute("class") or "").lower()
                if elem.is_enabled() and "disabled" not in classes:
                    return elem
            except NoSuchElementException:
                continue
        return None

    # --------------------------------------------------------------- Public API
    def run(self) -> List[QueryResult]:
        try:
            years = self._prepare_make_and_years()
        finally:
            self._close_main_driver()

        if not years:
            LOGGER.warning("No model years discovered for first vehicle make.")
            return []

        worker_count = min(max(1, self.workers), len(years))
        year_batches = self._split_years(years, worker_count)
        LOGGER.info(
            "Processing %d year(s) with %d worker(s) (avg %.2f years/worker)",
            len(years),
            worker_count,
            len(years) / worker_count,
        )

        results: List[QueryResult] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {}
            for idx, batch in enumerate(year_batches):
                if not batch:
                    continue
                worker_name = f"worker-{idx + 1}"
                LOGGER.info("%s assigned years: %s", worker_name, ", ".join(batch))
                future = executor.submit(self._run_worker, worker_name, batch)
                future_map[future] = worker_name

            for future in as_completed(future_map):
                worker_name = future_map[future]
                try:
                    results.extend(future.result())
                except Exception as exc:  # pylint: disable=broad-except
                    LOGGER.error("%s crashed: %s", worker_name, exc)

        return results

    def _split_years(self, years: Sequence[str], worker_count: int) -> List[List[str]]:
        batches: List[List[str]] = [[] for _ in range(worker_count)]
        for index, year in enumerate(years):
            batches[index % worker_count].append(year)
        return batches


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect CARB Vehicle Search results for the first make."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel workers (launches one browser per worker).",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Disable headless mode so Chrome windows remain visible.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=25,
        help="Seconds to wait for dropdowns, postbacks, and results.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Verbosity for stdout logging.",
    )
    return parser.parse_args()


def print_report(first_make: str, results: Iterable[QueryResult]) -> None:
    results = list(results)
    if not results:
        print("No results were gathered.")
        return

    total_records = sum(item.record_count for item in results)
    print("=" * 72)
    print(f"Vehicle make: {first_make}")
    print(f"Combinations processed: {len(results)}")
    print(f"Total records for {first_make}: {total_records}")
    print("-" * 72)

    for item in sorted(results, key=lambda r: (r.year, r.model, r.engine or "")):
        engine_label = item.engine or "ALL ENGINES"
        print(
            f"[{item.worker}] Year {item.year} | Model {item.model} | Engine {engine_label} "
            f"=> {item.record_count} record(s)"
        )
    print("=" * 72)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    runner = TestCarRecordsRunner(
        headless=not args.show_browser,
        timeout=args.timeout,
        workers=args.workers,
    )
    results = runner.run()
    print_report(runner.first_make or "Unknown", results)


if __name__ == "__main__":
    main()
