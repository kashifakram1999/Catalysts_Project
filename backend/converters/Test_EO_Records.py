#!/usr/bin/env python3
"""
Test_EO_Records
===============

Exercise the EO Search tab by iterating EO numbers from the dropdown, executing
the search for each EO, and counting how many rows appear in the results grid.
The script supports concurrent workers (one Chrome instance per worker) and
prints per-EO counts plus an aggregate total.

Usage:
    python backend/converters/Test_EO_Records.py --workers 8 --limit 100
"""

from __future__ import annotations

import argparse
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


LOGGER = logging.getLogger("Test_EO_Records")

BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"
EO_TAB_LOCATOR = (By.LINK_TEXT, "EO Search")
EO_TAB_FALLBACK = (By.PARTIAL_LINK_TEXT, "EO Search")
EO_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnARBEONumbers"
EO_OPTION_XPATH = (
    "//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers')]"
)
SEARCH_BUTTON_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_btnEOSearch"
RESULTS_TABLE_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData"
PAGE_SIZE = 25
MAX_EO_RETRIES = 3
PAGE_SIZE = 25


@dataclass
class EOResult:
    eo_number: str
    record_count: int
    worker: str


class DropdownSelectionError(Exception):
    """Raised when a dropdown option cannot be selected."""


class TestEORecordsRunner:
    def __init__(self, *, headless: bool = True, timeout: int = 25, workers: int = 1, limit: Optional[int] = None):
        self.headless = headless
        self.timeout = timeout
        self.workers = max(1, workers)
        self.limit = limit
        self._driver: Optional[webdriver.Chrome] = None
        self._log_lock = threading.Lock()

    # ------------------------------------------------------------------ drivers
    def _create_driver(self) -> webdriver.Chrome:
        options = webdriver.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
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

    def _initialize_worker(self, driver: webdriver.Chrome) -> None:
        driver.get(BASE_URL)
        self._wait_for_ready_state(driver, delay=2)
        self._open_eo_tab(driver)

    # ------------------------------------------------------------------ helpers
    def _wait_for_ready_state(self, driver: webdriver.Chrome, delay: float = 1.0) -> None:
        try:
            WebDriverWait(driver, self.timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            LOGGER.debug("Ignoring readyState timeout")
        time.sleep(delay)

    def _open_eo_tab(self, driver: webdriver.Chrome) -> None:
        try:
            tab = WebDriverWait(driver, self.timeout).until(EC.element_to_be_clickable(EO_TAB_LOCATOR))
        except TimeoutException:
            tab = WebDriverWait(driver, self.timeout).until(EC.element_to_be_clickable(EO_TAB_FALLBACK))
        driver.execute_script("arguments[0].click();", tab)
        time.sleep(1.5)

    def _collect_eo_numbers(self) -> List[str]:
        driver = self._ensure_driver()
        driver.get(BASE_URL)
        self._wait_for_ready_state(driver, delay=2)
        self._open_eo_tab(driver)

        numbers: List[str] = []
        dropdown = WebDriverWait(driver, self.timeout).until(
            EC.element_to_be_clickable((By.ID, EO_BUTTON_ID))
        )
        driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(1)

        options = driver.find_elements(By.XPATH, EO_OPTION_XPATH)
        for option in options:
            text = option.text.strip()
            match = re.search(r"(D-\d+-\d+)", text)
            if match:
                numbers.append(match.group(1))

        driver.execute_script("document.body.click();")
        LOGGER.info("Discovered %d EO numbers", len(numbers))
        if self.limit:
            numbers = numbers[: self.limit]
            LOGGER.info("Limiting to first %d EO numbers", len(numbers))
        return numbers

    def _select_eo_number(self, driver: webdriver.Chrome, eo_number: str) -> None:
        dropdown = WebDriverWait(driver, self.timeout).until(
            EC.element_to_be_clickable((By.ID, EO_BUTTON_ID))
        )
        driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(0.5)

        option_xpath = (
            f"//ul[@class='dropdown-menu scrollable-menu']//li/a[contains(@href, 'rptrARBEONumbers') "
            f"and contains(text(), '{eo_number}')]"
        )
        option = WebDriverWait(driver, self.timeout).until(
            EC.presence_of_element_located((By.XPATH, option_xpath))
        )

        href = option.get_attribute("href") or ""
        match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
        if match:
            target, argument = match.group(1), match.group(2)
            driver.execute_script(
                """
                var theForm = document.forms[0];
                theForm.__EVENTTARGET.value = arguments[0];
                theForm.__EVENTARGUMENT.value = arguments[1];
                theForm.submit();
                """,
                target,
                argument,
            )
        else:
            driver.execute_script("arguments[0].click();", option)

        self._wait_for_ready_state(driver, delay=2.0)

    # ------------------------------------------------------------------ workers
    def run(self) -> List[EOResult]:
        try:
            eo_numbers = self._collect_eo_numbers()
        finally:
            self._close_main_driver()

        if not eo_numbers:
            LOGGER.warning("No EO numbers discovered.")
            return []

        worker_count = min(self.workers, len(eo_numbers))
        batches = self._split_list(eo_numbers, worker_count)
        LOGGER.info("Processing %d EO numbers with %d worker(s)", len(eo_numbers), worker_count)

        results: List[EOResult] = []
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            future_map = {}
            for idx, batch in enumerate(batches):
                if not batch:
                    continue
                worker = f"worker-{idx + 1}"
                LOGGER.info("%s handling %d EO numbers", worker, len(batch))
                future = executor.submit(self._run_worker, worker, batch)
                future_map[future] = worker

            for future in as_completed(future_map):
                worker = future_map[future]
                try:
                    results.extend(future.result())
                except Exception as exc:  # pylint: disable=broad-except
                    LOGGER.error("%s crashed: %s", worker, exc)

        return results

    def _run_worker(self, worker_name: str, eo_numbers: Sequence[str]) -> List[EOResult]:
        results: List[EOResult] = []
        driver = self._create_driver()
        try:
            self._initialize_worker(driver)

            for eo_number in eo_numbers:
                attempt = 1
                while attempt <= MAX_EO_RETRIES:
                    try:
                        result = self._process_eo(driver, worker_name, eo_number)
                        if result:
                            results.append(result)
                        break
                    except Exception as exc:  # pylint: disable=broad-except
                        message = repr(exc) if not str(exc) else str(exc)
                        with self._log_lock:
                            LOGGER.error(
                                "[%s] Failed EO %s (attempt %d/%d): %s",
                                worker_name,
                                eo_number,
                                attempt,
                                MAX_EO_RETRIES,
                                message,
                            )
                        attempt += 1
                        if attempt <= MAX_EO_RETRIES:
                            self._initialize_worker(driver)
                        else:
                            with self._log_lock:
                                LOGGER.error("[%s] Giving up on EO %s after %d attempts", worker_name, eo_number, MAX_EO_RETRIES)
        finally:
            try:
                driver.quit()
            except WebDriverException:
                pass

        return results

    def _process_eo(self, driver: webdriver.Chrome, worker_name: str, eo_number: str) -> Optional[EOResult]:
        with self._log_lock:
            LOGGER.info("[%s] Processing EO %s", worker_name, eo_number)

        self._open_eo_tab(driver)
        self._select_eo_number(driver, eo_number)
        self._open_eo_tab(driver)  # Postback jumps to Vehicle tab; return to EO tab

        search_button = WebDriverWait(driver, self.timeout).until(
            EC.element_to_be_clickable((By.ID, SEARCH_BUTTON_ID))
        )
        driver.execute_script("arguments[0].click();", search_button)
        self._wait_for_ready_state(driver, delay=2.0)

        count = self._count_results(driver)

        with self._log_lock:
            LOGGER.info("[%s] EO %s => %d record(s)", worker_name, eo_number, count)

        return EOResult(eo_number=eo_number, record_count=count, worker=worker_name)

    def _count_results(self, driver: webdriver.Chrome) -> int:
        def table_present(drv: webdriver.Chrome) -> bool:
            try:
                drv.find_element(By.ID, RESULTS_TABLE_ID)
                return True
            except NoSuchElementException:
                return False

        def no_data_present(drv: webdriver.Chrome) -> bool:
            try:
                label = drv.find_element(By.XPATH, "//span[contains(@id, 'lblEO') and contains(translate(text(),'NO','no'), 'no')]")
                return bool(label.text.strip())
            except NoSuchElementException:
                return False

        try:
            WebDriverWait(driver, self.timeout).until(lambda d: table_present(d) or no_data_present(d))
        except TimeoutException:
            LOGGER.warning("Timed out waiting for EO results - assuming 0 rows")
            return 0

        if no_data_present(driver):
            return 0

        first_page_rows = self._count_rows_on_current_page(driver)
        total_pages = self._determine_total_pages_fast(driver)

        if total_pages <= 1:
            return first_page_rows

        if not self._jump_to_page(driver, target_page=total_pages):
            LOGGER.info("Failed to jump to last page; falling back to sequential count")
            return self._count_rows_sequential(driver, first_page_rows)

        last_page_rows = self._count_rows_on_current_page(driver)
        total = (total_pages - 1) * PAGE_SIZE + last_page_rows
        return total

    def _split_list(self, values: Sequence[str], bucket_count: int) -> List[List[str]]:
        buckets: List[List[str]] = [[] for _ in range(bucket_count)]
        for index, value in enumerate(values):
            buckets[index % bucket_count].append(value)
        return buckets

    def _count_rows_on_current_page(self, driver: webdriver.Chrome) -> int:
        try:
            table = driver.find_element(By.ID, RESULTS_TABLE_ID)
        except NoSuchElementException:
            return 0
        rows = table.find_elements(By.XPATH, ".//tr[td]")
        return len(rows)

    def _count_rows_sequential(self, driver: webdriver.Chrome, initial_rows: int) -> int:
        total_rows = initial_rows
        page_num = 1

        guard = 0
        while True:
            try:
                current_table = driver.find_element(By.ID, RESULTS_TABLE_ID)
            except NoSuchElementException:
                break

            next_link = self._find_next_number_link(driver, page_num + 1)
            if not next_link:
                visible_max = self._extract_visible_max_page(driver)
                next_link = self._find_trailing_ellipsis(driver, require_after_page=visible_max)

            if not next_link:
                break

            self._activate_pagination_link(driver, next_link, current_table, (By.ID, RESULTS_TABLE_ID))
            page_num += 1
            total_rows += self._count_rows_on_current_page(driver)
            guard += 1
            if guard > 200:
                LOGGER.warning("Sequential fallback bailed after 200 pages")
                break

        return total_rows

    def _activate_pagination_link(
        self,
        driver: webdriver.Chrome,
        link,
        current_table,
        table_locator,
    ) -> None:
        href = link.get_attribute("href") or ""
        if "__doPostBack" in href:
            match = re.search(r"__doPostBack\('([^']+)','([^']*)'\)", href)
            if match:
                target, argument = match.groups()
                driver.execute_script(
                    """
                    var theForm = document.forms[0];
                    theForm.__EVENTTARGET.value = arguments[0];
                    theForm.__EVENTARGUMENT.value = arguments[1];
                    theForm.submit();
                    """,
                    target,
                    argument,
                )
            else:
                driver.execute_script("arguments[0].click();", link)
        else:
            driver.execute_script("arguments[0].click();", link)

        WebDriverWait(driver, self.timeout).until(EC.staleness_of(current_table))
        self._open_eo_tab(driver)
        WebDriverWait(driver, self.timeout).until(
            EC.presence_of_element_located(table_locator)
        )
        time.sleep(1.0)

    def _determine_total_pages_fast(self, driver: webdriver.Chrome) -> int:
        max_page = self._extract_visible_max_page(driver)
        while True:
            ellipsis = self._find_trailing_ellipsis(driver, require_after_page=max_page)
            if not ellipsis:
                break
            try:
                current_table = driver.find_element(By.ID, RESULTS_TABLE_ID)
            except NoSuchElementException:
                break
            self._activate_pagination_link(driver, ellipsis, current_table, (By.ID, RESULTS_TABLE_ID))
            visible_max = self._extract_visible_max_page(driver)
            max_page = max(max_page, visible_max)
        return max_page or 1

    def _extract_visible_max_page(self, driver: webdriver.Chrome) -> int:
        try:
            pagination_row = driver.find_element(
                By.XPATH,
                "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]",
            )
        except NoSuchElementException:
            return 1

        numbers = []
        for control in pagination_row.find_elements(By.XPATH, ".//a | .//span"):
            text = control.text.strip()
            if text.isdigit():
                numbers.append(int(text))
        return max(numbers) if numbers else 1

    def _find_trailing_ellipsis(self, driver: webdriver.Chrome, require_after_page: Optional[int] = None):
        try:
            pagination_row = driver.find_element(
                By.XPATH,
                "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']//tr[last()]",
            )
        except NoSuchElementException:
            return None

        controls = pagination_row.find_elements(By.XPATH, ".//a | .//span")
        after_target = require_after_page is None
        ellipsis_candidate = None
        for control in controls:
            text = control.text.strip()
            if not text:
                continue

            if not after_target and text.isdigit() and int(text) == require_after_page:
                after_target = True
                continue

            if after_target and text == "..." and control.tag_name.lower() == "a":
                ellipsis_candidate = control

        return ellipsis_candidate

    def _find_next_number_link(self, driver: webdriver.Chrome, target_page: int):
        selector = (
            "//table[@id='ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData']"
            f"//tr[last()]//a[normalize-space(text())='{target_page}']"
        )
        try:
            return driver.find_element(By.XPATH, selector)
        except NoSuchElementException:
            return None

    def _jump_to_page(self, driver: webdriver.Chrome, target_page: int) -> bool:
        attempts = 0
        while attempts < 20:
            link = self._find_next_number_link(driver, target_page)
            if link:
                try:
                    current_table = driver.find_element(By.ID, RESULTS_TABLE_ID)
                except NoSuchElementException:
                    return False
                self._activate_pagination_link(driver, link, current_table, (By.ID, RESULTS_TABLE_ID))
                return True

            ellipsis = self._find_trailing_ellipsis(driver)
            if not ellipsis:
                break

            try:
                current_table = driver.find_element(By.ID, RESULTS_TABLE_ID)
            except NoSuchElementException:
                return False

            self._activate_pagination_link(driver, ellipsis, current_table, (By.ID, RESULTS_TABLE_ID))
            attempts += 1

        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect counts for EO Search results.")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel browser instances.")
    parser.add_argument("--show-browser", action="store_true", help="Disable headless mode.")
    parser.add_argument(
        "--browser-mode",
        action="store_true",
        help="Alias for --show-browser (kept for clarity when debugging visually).",
    )
    parser.add_argument("--timeout", type=int, default=25, help="Seconds to wait for dropdowns/results.")
    parser.add_argument("--limit", type=int, help="Only process the first N EO numbers.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return parser.parse_args()


def print_report(results: Iterable[EOResult]) -> None:
    results = list(results)
    if not results:
        print("No EO results gathered.")
        return

    total = sum(item.record_count for item in results)
    print("=" * 72)
    print(f"EOs processed: {len(results)}")
    print(f"Total rows scraped: {total}")
    print("-" * 72)
    for item in results:
        print(f"[{item.worker}] EO {item.eo_number} => {item.record_count} record(s)")
    print("=" * 72)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    show_browser = args.show_browser or args.browser_mode
    runner = TestEORecordsRunner(
        headless=not show_browser,
        timeout=args.timeout,
        workers=args.workers,
        limit=args.limit,
    )
    results = runner.run()
    print_report(results)


if __name__ == "__main__":
    main()
