#!/usr/bin/env python3
"""
HTTP-first CARB EO scraper.

Replaces the unstable Selenium pagination path with a pure requests-based
WebForms client that:
- Replays __VIEWSTATE / __EVENTVALIDATION for every POST
- Navigates pagination via __doPostBack arguments
- Persists EO-level progress so runs can resume from the last good page
- Writes page-by-page inside transaction.atomic() with bulk_create(ignore_conflicts=True)
"""

import logging
import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import CatalyticConverter, EOProgress, Manufacturer, ScraperRun

logger = logging.getLogger(__name__)

POSTBACK_REGEX = re.compile(r"__doPostBack\('(?P<target>[^']+)','(?P<argument>[^']*)'\)")
RESULTS_TABLE_ID = "ctl00_ctl00_MainContent_ARBDBBodyContent_UCEOSearch_gvEOData"
EO_LINK_FRAGMENT = "rptrARBEONumbers"
SEARCH_BUTTON_FRAGMENT = "btnEOSearch"
TARGET_TOTAL_ROWS = 991_254
MAX_RETRIES = 3
BACKOFF_SCHEDULE = [2, 5, 10]
DEFAULT_TIMEOUT = 30


@dataclass
class PagePersistResult:
    attempted: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class CARBEOScraper:
    """EO scraper that talks to the ASP.NET WebForms endpoint over HTTP."""

    BASE_URL = "https://ssl.arb.ca.gov/AftermarketParts/catalysts"

    def __init__(self, headless: bool = True, timeout: int = 20, pages_per_eo: Optional[int] = None):
        self.timeout = timeout or DEFAULT_TIMEOUT
        self.pages_per_eo = pages_per_eo if pages_per_eo else None
        self.session: Optional[requests.Session] = None
        self.pagination_target: Optional[str] = None
        self.manufacturer_cache: Dict[str, Manufacturer] = {}
        self.results_table_id: str = RESULTS_TABLE_ID
        self._debug_logged_form_info = False
        self._last_response_status: Optional[int] = None
        self._last_response_snippet: str = ""

    # ------------------------------------------------------------------ #
    # Session lifecycle                                                  #
    # ------------------------------------------------------------------ #
    def _setup_driver(self):
        """Initialize the requests session (keeps interface for callers intact)."""
        if self.session:
            return

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Origin": "https://ssl.arb.ca.gov",
            "Referer": self.BASE_URL,
        })
        logger.info("HTTP session initialized for CARB scraper")

    def _close_driver(self):
        """Close the session."""
        if self.session:
            try:
                self.session.close()
            finally:
                self.session = None
                logger.info("HTTP session closed")

    # ------------------------------------------------------------------ #
    # HTTP helpers                                                       #
    # ------------------------------------------------------------------ #
    def _request(self, method: str, data: Optional[Dict] = None, description: str = "", url: Optional[str] = None) -> BeautifulSoup:
        """Perform a request with retries and return BeautifulSoup."""
        if not self.session:
            self._setup_driver()

        last_exc: Optional[Exception] = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                target_url = url or self.BASE_URL
                resp = self.session.request(method, target_url, data=data, timeout=self.timeout)
                resp.raise_for_status()
                self._last_response_status = resp.status_code
                self._last_response_snippet = (resp.text or "")[:300]
                return BeautifulSoup(resp.text, "lxml")
            except Exception as exc:  # requests.RequestException and parse errors
                last_exc = exc
                wait = BACKOFF_SCHEDULE[min(attempt - 1, len(BACKOFF_SCHEDULE) - 1)]
                logger.warning(
                    f"{description or method} failed (attempt {attempt}/{MAX_RETRIES}): {exc}. "
                    f"Retrying in {wait}s"
                )
                time.sleep(wait)

        raise last_exc  # type: ignore[misc]

    def _extract_form_fields(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Return all input name/value pairs required for a WebForms POST."""
        fields: Dict[str, str] = {}
        for tag in soup.find_all("input"):
            name = tag.get("name")
            if not name:
                continue

            input_type = (tag.get("type") or "").lower()
            if input_type in {"submit", "button", "image"}:
                continue

            if input_type in {"checkbox", "radio"} and not tag.has_attr("checked"):
                continue

            fields[name] = tag.get("value", "")

        return fields

    def _parse_postback(self, href: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract __EVENTTARGET and __EVENTARGUMENT from a __doPostBack href."""
        match = POSTBACK_REGEX.search(href or "")
        if not match:
            return None, None
        return match.group("target"), match.group("argument")

    def _postback(
        self,
        soup: BeautifulSoup,
        event_target: Optional[str],
        event_argument: Optional[str] = "",
        extra_fields: Optional[Dict[str, str]] = None,
        description: str = "postback",
    ) -> BeautifulSoup:
        """Send a WebForms postback using the current page state."""
        payload = self._extract_form_fields(soup)
        if event_target is not None:
            payload["__EVENTTARGET"] = event_target
        if event_argument is not None:
            payload["__EVENTARGUMENT"] = event_argument
        if extra_fields:
            payload.update(extra_fields)

        form = soup.find("form")
        action = form.get("action") if form else None
        target_url = urljoin(self.BASE_URL, action) if action else self.BASE_URL

        return self._request("POST", data=payload, description=description, url=target_url)

    def _activate_eo_tab(self, soup: BeautifulSoup) -> BeautifulSoup:
        """Ensure the EO Search tab is active."""
        link = soup.find("a", string=re.compile(r"EO Search", re.IGNORECASE))
        if not link:
            return soup

        target, argument = self._parse_postback(link.get("href", ""))
        if not target:
            return soup

        logger.info("Activating EO Search tab via HTTP postback")
        return self._postback(soup, target, argument, description="activate EO Search tab")

    def _log_form_diagnostics(self, soup: BeautifulSoup):
        """Log one-time form and control hints to help debug."""
        if self._debug_logged_form_info:
            return

        form = soup.find("form")
        action = form.get("action") if form else None

        search_button = None
        for candidate in soup.find_all(["input", "button", "a"]):
            cid = candidate.get("id", "")
            cname = candidate.get("name", "")
            href = candidate.get("href", "")
            if SEARCH_BUTTON_FRAGMENT in cid or SEARCH_BUTTON_FRAGMENT in cname or SEARCH_BUTTON_FRAGMENT in href:
                search_button = candidate
                break

        table_id = None
        table = soup.find("table", id=re.compile(r"gvEO", re.IGNORECASE)) or soup.find("table", id=re.compile(r"gvEOData", re.IGNORECASE))
        if table:
            table_id = table.get("id")

        pager_target = None
        for anchor in soup.find_all("a", href=True):
            m = POSTBACK_REGEX.search(anchor["href"])
            if not m:
                continue
            if (m.group("argument") or "").startswith("Page$"):
                pager_target = m.group("target")
                break

        logger.info(
            f"[DEBUG] Form action={action or '<none>'}, search_button_id={search_button.get('id') if search_button else '<none>'}, "
            f"search_button_name={search_button.get('name') if search_button else '<none>'}, "
            f"results_table_id={table_id or '<none>'}, pager_event_target={pager_target or '<none>'}"
        )
        self._debug_logged_form_info = True

    def _dump_debug_html(self, eo_number: str, stage: str, soup: BeautifulSoup):
        """Persist a debug HTML snapshot to help diagnose failures."""
        try:
            debug_dir = Path(__file__).resolve().parent.parent / "data"
            debug_dir.mkdir(parents=True, exist_ok=True)
            path = debug_dir / f"debug_{eo_number}_{stage}.html"
            path.write_text(str(soup)[:500000], encoding="utf-8")
            logger.info(f"[DEBUG] Saved HTML snapshot to {path}")
        except Exception as exc:
            logger.warning(f"[DEBUG] Failed to write HTML snapshot for {eo_number} at {stage}: {exc}")

    # ------------------------------------------------------------------ #
    # Data extraction helpers                                            #
    # ------------------------------------------------------------------ #
    def extract_eo_numbers(self) -> List[str]:
        """Pull EO numbers from the dropdown menu."""
        logger.info("=" * 60)
        logger.info("EXTRACTING EO NUMBERS (HTTP)")
        logger.info("=" * 60)

        soup = self._request("GET", description="load EO landing page")
        soup = self._activate_eo_tab(soup)

        eo_numbers: List[str] = []
        for anchor in soup.find_all("a", href=True):
            if EO_LINK_FRAGMENT not in anchor.get("href", ""):
                continue
            text = (anchor.get_text() or "").strip()
            match = re.search(r"(D-\d+-\d+)", text)
            if match:
                eo_numbers.append(match.group(1))

        logger.info(f"✓ Extracted {len(eo_numbers)} EO numbers from dropdown")
        return eo_numbers

    # ------------------------------------------------------------------ #
    # Pagination + table parsing                                         #
    # ------------------------------------------------------------------ #
    def _derive_pagination_target(self, soup: BeautifulSoup) -> None:
        """Capture the grid's __EVENTTARGET used for paging."""
        if self.pagination_target:
            return

        grid = self._find_results_table(soup)
        anchor_source = []
        if grid:
            pager_row = self._pager_row(grid)
            if pager_row:
                anchor_source = pager_row.find_all("a", href=True)
        if not anchor_source:
            anchor_source = soup.find_all("a", href=True)

        for anchor in anchor_source:
            match = POSTBACK_REGEX.search(anchor["href"])
            if not match:
                continue
            argument = match.group("argument") or ""
            if argument.startswith("Page$"):
                self.pagination_target = match.group("target")
                return

    def _pager_row(self, table: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Locate the pager row within the results table."""
        rows = table.find_all("tr")
        for row in reversed(rows):
            if row.find("a") or row.find("span"):
                # Heuristic: row that contains numeric pager buttons/ellipsis
                texts = [t.strip() for t in row.stripped_strings]
                if any(t.isdigit() or "..." in t for t in texts):
                    return row
        return None

    def _max_visible_page(self, soup: BeautifulSoup) -> Optional[int]:
        """Return the highest page number currently rendered (pager row only)."""
        table = self._find_results_table(soup)
        if not table:
            return None
        pager = self._pager_row(table)
        if not pager:
            return None

        page_numbers: List[int] = []
        for element in pager.find_all(["a", "span"]):
            text = (element.get_text() or "").strip()
            if text.isdigit():
                try:
                    page_numbers.append(int(text))
                except ValueError:
                    continue
        return max(page_numbers) if page_numbers else None

    def _current_page(self, soup: BeautifulSoup) -> int:
        """Detect the current page number from the pagination footer."""
        table = self._find_results_table(soup)
        if table:
            pager = self._pager_row(table)
            if pager:
                for element in pager.find_all("span"):
                    text = (element.get_text() or "").strip()
                    if text.isdigit():
                        try:
                            return int(text)
                        except ValueError:
                            continue
        return 1

    def _clamp_pages(self, current_page: int, visible_page: Optional[int]) -> int:
        """
        Clamp unreasonable pager numbers to avoid bogus large values.
        Allows a generous window of +1000 pages over current.
        """
        if not visible_page:
            return current_page
        if visible_page > current_page + 1000:
            logger.warning(f"[DEBUG] Clamping visible page {visible_page} to {current_page} (suspiciously high)")
            return current_page
        return visible_page

    def _next_page_argument(self, soup: BeautifulSoup, current_page: int) -> Optional[str]:
        """
        Determine the correct __EVENTARGUMENT for the next page.
        Tries an explicit Page$N link, then Page$Next if present.
        """
        next_page = current_page + 1
        grid = self._find_results_table(soup)
        anchor_source = []
        if grid:
            pager_row = self._pager_row(grid)
            if pager_row:
                anchor_source = pager_row.find_all("a", href=True)
        if not anchor_source:
            anchor_source = soup.find_all("a", href=True)

        for anchor in anchor_source:
            href = anchor["href"]
            match = POSTBACK_REGEX.search(href)
            if not match:
                continue
            argument = match.group("argument") or ""
            if argument == "Page$Next":
                self.pagination_target = match.group("target")
                return f"Page${next_page}"
            if argument == f"Page${next_page}":
                self.pagination_target = match.group("target")
                return argument

        return None

    def _goto_page(self, soup: BeautifulSoup, page_number: int) -> Optional[BeautifulSoup]:
        """Navigate to a specific page using the grid postback."""
        self._derive_pagination_target(soup)
        if not self.pagination_target:
            return None

        logger.info(f"Requesting page {page_number} via HTTP postback")
        try:
            return self._postback(
                soup,
                self.pagination_target,
                f"Page${page_number}",
                description=f"paginate to page {page_number}",
            )
        except Exception as exc:
            logger.warning(f"Failed to move to page {page_number}: {exc}")
            return None

    def _find_results_table(self, soup: BeautifulSoup):
        """Locate the results table using multiple heuristics and cache the id."""
        table = soup.find("table", id=self.results_table_id)
        if table:
            return table

        candidates = soup.find_all("table", id=re.compile(r"gvEO", re.IGNORECASE))
        if not candidates:
            candidates = soup.find_all("table", id=re.compile(r"gvEOData", re.IGNORECASE))
        if not candidates:
            for tbl in soup.find_all("table"):
                headers = " ".join(h.get_text(strip=True).lower() for h in tbl.find_all("th"))
                if headers and ("make" in headers and "model" in headers and "test" in headers):
                    candidates.append(tbl)

        if candidates:
            self.results_table_id = candidates[0].get("id") or self.results_table_id
            return candidates[0]
        return None

    def _is_error_page(self, soup: BeautifulSoup) -> bool:
        """Detect the CARB error page."""
        text = soup.get_text(" ", strip=True).lower()
        if "an error has occurred" in text or "unexpected error occurred" in text:
            return True
        form = soup.find("form")
        action = form.get("action", "") if form else ""
        return "error.aspx" in action.lower()

    def _recover_page(self, eo_number: str, target_page: int) -> Optional[BeautifulSoup]:
        """Attempt to recover from an error page by reloading the session and returning to the target page."""
        logger.warning(f"[DEBUG] Attempting recovery for EO {eo_number} page {target_page}")
        try:
            self._close_driver()
            time.sleep(1)
            self._setup_driver()
            soup = self._request("GET", description="recover load base page")
            soup = self._activate_eo_tab(soup)
            soup = self._select_eo(soup, eo_number)
            if not soup:
                return None
            soup = self._activate_eo_tab(soup)
            soup = self._submit_search(soup)
            if not soup:
                return None
            table = self._find_results_table(soup)
            if not table:
                return None
            self._derive_pagination_target(soup)
            if target_page > 1:
                soup = self._goto_page(soup, target_page)
            return soup
        except Exception as exc:
            logger.warning(f"[DEBUG] Recovery failed for EO {eo_number} page {target_page}: {exc}")
            return None

    def _parse_table_rows(self, soup: BeautifulSoup, eo_number: str) -> List[Dict]:
        """Convert the results table into a list of converter dictionaries."""
        table = self._find_results_table(soup)
        if not table:
            return []

        converters: List[Dict] = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 14:
                continue

            def cell(idx: int) -> str:
                return cells[idx].get_text(strip=True)

            model_year_text = cell(1)
            try:
                model_year_start = int(model_year_text) if model_year_text else None
            except ValueError:
                model_year_start = None

            quantity_text = cell(11)
            try:
                quantity = int(quantity_text) if quantity_text.isdigit() else None
            except Exception:
                quantity = None

            converters.append({
                "executive_order": eo_number,
                "make": cell(0),
                "model_year_start": model_year_start,
                "model_year_end": model_year_start,
                "model": cell(2),
                "engine_size": cell(3),
                "application_type": cell(4),
                "manufacturer_name": cell(5) or "Unknown",
                "series_model": cell(6),
                "part_number": cell(6),
                "test_group": cell(7),
                "cert_level": cell(8),
                "vehicle_class": cell(10),
                "quantity": quantity,
                "converter_location": cell(12),
                "converter_type": cell(13),
            })

        return converters

    # ------------------------------------------------------------------ #
    # Persistence helpers                                                #
    # ------------------------------------------------------------------ #
    def _get_manufacturers(self, names: List[str]) -> Dict[str, Manufacturer]:
        """Fetch or create manufacturers in bulk, cached by name."""
        normalized = [name or "Unknown" for name in names]
        missing = [n for n in normalized if n not in self.manufacturer_cache]

        if missing:
            existing = Manufacturer.objects.filter(name__in=missing).in_bulk(field_name="name")
            self.manufacturer_cache.update(existing)

            to_create = [Manufacturer(name=name) for name in missing if name not in existing]
            if to_create:
                Manufacturer.objects.bulk_create(to_create, ignore_conflicts=True)
                refreshed = Manufacturer.objects.filter(name__in=missing).in_bulk(field_name="name")
                self.manufacturer_cache.update(refreshed)

        return {name: self.manufacturer_cache[name] for name in normalized}

    def _signature_from_row(self, row: Dict, manufacturer_name: str) -> Tuple:
        """Build a tuple representing the unique constraint used for deduping."""
        return (
            (manufacturer_name or "").strip().lower(),
            (row.get("executive_order") or "").strip().lower(),
            (row.get("test_group") or "").strip().lower(),
            (row.get("part_number") or "").strip().lower(),
            (row.get("series_model") or "").strip().lower(),
            (row.get("make") or "").strip().lower(),
            (row.get("model") or "").strip().lower(),
            row.get("model_year_start"),
            row.get("model_year_end"),
            (row.get("converter_location") or "").strip().lower(),
            (row.get("converter_type") or "").strip().lower(),
            (row.get("application_type") or "").strip().lower(),
            (row.get("cert_level") or "").strip().lower(),
            (row.get("vehicle_class") or "").strip().lower(),
            (row.get("engine_size") or "").strip().lower(),
            row.get("quantity"),
        )

    def _signature_from_values(self, values: Dict) -> Tuple:
        """Signature helper for existing DB rows."""
        return (
            (values.get("manufacturer__name") or "").strip().lower(),
            (values.get("executive_order") or "").strip().lower(),
            (values.get("test_group") or "").strip().lower(),
            (values.get("part_number") or "").strip().lower(),
            (values.get("series_model") or "").strip().lower(),
            (values.get("make") or "").strip().lower(),
            (values.get("model") or "").strip().lower(),
            values.get("model_year_start"),
            values.get("model_year_end"),
            (values.get("converter_location") or "").strip().lower(),
            (values.get("converter_type") or "").strip().lower(),
            (values.get("application_type") or "").strip().lower(),
            (values.get("cert_level") or "").strip().lower(),
            (values.get("vehicle_class") or "").strip().lower(),
            (values.get("engine_size") or "").strip().lower(),
            values.get("quantity"),
        )

    def _persist_page(self, eo_number: str, rows: List[Dict], page_number: int) -> PagePersistResult:
        """Save a single page's rows atomically using bulk_create(ignore_conflicts=True)."""
        attempted = len(rows)
        if attempted == 0:
            return PagePersistResult()

        manufacturer_names = [row.get("manufacturer_name") or "Unknown" for row in rows]
        manufacturers = self._get_manufacturers(manufacturer_names)
        now = timezone.now()

        existing = CatalyticConverter.objects.filter(
            executive_order=eo_number,
            manufacturer__name__in=manufacturer_names,
        ).values(
            "id",
            "executive_order",
            "manufacturer__name",
            "test_group",
            "part_number",
            "series_model",
            "make",
            "model",
            "model_year_start",
            "model_year_end",
            "converter_location",
            "converter_type",
            "application_type",
            "cert_level",
            "vehicle_class",
            "engine_size",
            "quantity",
        )

        existing_signatures = {self._signature_from_values(row): row["id"] for row in existing}
        new_objects: List[CatalyticConverter] = []
        duplicate_ids: List[int] = []

        for row in rows:
            manufacturer_name = row.get("manufacturer_name") or "Unknown"
            signature = self._signature_from_row(row, manufacturer_name)
            if signature in existing_signatures:
                duplicate_ids.append(existing_signatures[signature])
                continue

            manufacturer = manufacturers[manufacturer_name]
            new_objects.append(CatalyticConverter(
                manufacturer=manufacturer,
                executive_order=row.get("executive_order"),
                series_model=row.get("series_model"),
                part_number=row.get("part_number"),
                product_name=None,
                model_year_start=row.get("model_year_start"),
                model_year_end=row.get("model_year_end"),
                make=row.get("make"),
                model=row.get("model"),
                vehicle_class=row.get("vehicle_class"),
                engine_size=row.get("engine_size"),
                test_group=row.get("test_group"),
                cert_level=row.get("cert_level"),
                application_type=row.get("application_type"),
                converter_location=row.get("converter_location"),
                converter_type=row.get("converter_type"),
                quantity=row.get("quantity"),
                eo_date=None,
                last_scraped=now,
            ))

        inserted = 0
        updated = 0
        try:
            with transaction.atomic():
                CatalyticConverter.objects.bulk_create(new_objects, ignore_conflicts=True)
                inserted = len(new_objects)
                if duplicate_ids:
                    updated = CatalyticConverter.objects.filter(id__in=set(duplicate_ids)).update(last_scraped=now)
        except IntegrityError as exc:
            # Fallback to row-by-row get_or_create to avoid crashing on unexpected constraints
            logger.warning(f"IntegrityError during bulk_create (fallback to per-row) for EO {eo_number}: {exc}")
            for row in rows:
                manufacturer_name = row.get("manufacturer_name") or "Unknown"
                manufacturer = manufacturers[manufacturer_name]
                defaults = {
                    "series_model": row.get("series_model"),
                    "part_number": row.get("part_number"),
                    "product_name": None,
                    "model_year_start": row.get("model_year_start"),
                    "model_year_end": row.get("model_year_end"),
                    "make": row.get("make"),
                    "model": row.get("model"),
                    "vehicle_class": row.get("vehicle_class"),
                    "engine_size": row.get("engine_size"),
                    "test_group": row.get("test_group"),
                    "cert_level": row.get("cert_level"),
                    "application_type": row.get("application_type"),
                    "converter_location": row.get("converter_location"),
                    "converter_type": row.get("converter_type"),
                    "quantity": row.get("quantity"),
                    "eo_date": None,
                    "last_scraped": now,
                }
                obj, created = CatalyticConverter.objects.get_or_create(
                    manufacturer=manufacturer,
                    executive_order=row.get("executive_order"),
                    test_group=row.get("test_group"),
                    part_number=row.get("part_number"),
                    series_model=row.get("series_model"),
                    converter_location=row.get("converter_location"),
                    converter_type=row.get("converter_type"),
                    make=row.get("make"),
                    model=row.get("model"),
                    model_year_start=row.get("model_year_start"),
                    model_year_end=row.get("model_year_end"),
                    engine_size=row.get("engine_size"),
                    application_type=row.get("application_type"),
                    cert_level=row.get("cert_level"),
                    vehicle_class=row.get("vehicle_class"),
                    quantity=row.get("quantity"),
                    defaults=defaults,
                )
                if created:
                    inserted += 1
                else:
                    obj.last_scraped = now
                    obj.save(update_fields=["last_scraped"])
                    updated += 1

        skipped = attempted - inserted
        logger.info(
            f"[{eo_number}] Page {page_number}: attempted={attempted}, inserted={inserted}, "
            f"skipped_duplicates={skipped}, updated_last_scraped={updated}"
        )
        return PagePersistResult(attempted=attempted, inserted=inserted, skipped=skipped, updated=updated)

    # ------------------------------------------------------------------ #
    # EO scraping                                                        #
    # ------------------------------------------------------------------ #
    def _load_progress(self, eo_number: str) -> EOProgress:
        progress, _ = EOProgress.objects.get_or_create(eo_number=eo_number)
        return progress

    def _stop_requested(self, scraper_run_id: Optional[int]) -> bool:
        if not scraper_run_id:
            return False
        try:
            return ScraperRun.objects.filter(id=scraper_run_id, stop_requested=True).exists()
        except Exception:
            return False

    def _select_eo(self, soup: BeautifulSoup, eo_number: str) -> Optional[BeautifulSoup]:
        """Trigger EO selection via dropdown or link postback."""
        # Prefer select element if present
        select = None
        for candidate in soup.find_all("select"):
            opts = [opt.get_text(strip=True) for opt in candidate.find_all("option")]
            if any(eo_number in (opt or "") for opt in opts):
                select = candidate
                break

        if select:
            value = None
            for opt in select.find_all("option"):
                if eo_number in (opt.get_text() or ""):
                    value = opt.get("value") or opt.get_text(strip=True)
                    break
            payload = self._extract_form_fields(soup)
            payload["__EVENTTARGET"] = select.get("name") or select.get("id") or ""
            payload["__EVENTARGUMENT"] = ""
            if value is not None:
                payload[select.get("name") or select.get("id") or ""] = value
            logger.info(f"Selecting EO {eo_number} via <select> postback target={payload.get('__EVENTTARGET')}")
            try:
                form = soup.find("form")
                action = form.get("action") if form else None
                target_url = urljoin(self.BASE_URL, action) if action else self.BASE_URL
                return self._request("POST", data=payload, description=f"select EO {eo_number} (select)", url=target_url)
            except Exception as exc:
                logger.warning(f"Select-based EO selection failed for {eo_number}: {exc}")

        for anchor in soup.find_all("a", href=True):
            if EO_LINK_FRAGMENT not in anchor.get("href", ""):
                continue
            if eo_number not in (anchor.get_text() or ""):
                continue
            target, argument = self._parse_postback(anchor["href"])
            if not target:
                continue
            logger.info(f"Selecting EO {eo_number} via postback target={target} argument={argument}")
            return self._postback(soup, target, argument, description=f"select EO {eo_number}")
        logger.warning(f"EO {eo_number} selection failed: no select/anchor trigger found")
        return None

    def _submit_search(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """Click the search button through an HTTP POST."""
        button = None
        candidates = []
        for candidate in soup.find_all(["input", "button", "a"]):
            cid = candidate.get("id", "")
            cname = candidate.get("name", "")
            href = candidate.get("href", "")
            if SEARCH_BUTTON_FRAGMENT in cid or SEARCH_BUTTON_FRAGMENT in cname or SEARCH_BUTTON_FRAGMENT in href:
                button = candidate
                break
            candidates.append((cid, cname, href))
        if not button:
            logger.warning(f"Search button not found in DOM; candidates={candidates[:5]}")
            self._dump_debug_html("unknown", "search_button_missing", soup)
            return None

        # If anchor with __doPostBack, use target/argument
        if button.name == "a" and button.get("href"):
            target, argument = self._parse_postback(button["href"])
            if target:
                logger.info(f"Submitting EO search via anchor postback target={target}")
                return self._postback(soup, target, argument, description="submit EO search (anchor)")

        button_name = button.get("name") or button.get("id")
        button_value = button.get("value", button.get_text(strip=True) or "Search")
        logger.info(f"Submitting EO search via HTTP (button_name={button_name})")
        try:
            payload = self._extract_form_fields(soup)
            payload["__EVENTTARGET"] = ""
            payload["__EVENTARGUMENT"] = ""
            if button_name:
                payload[button_name] = button_value
            form = soup.find("form")
            action = form.get("action") if form else None
            target_url = urljoin(self.BASE_URL, action) if action else self.BASE_URL
            return self._request("POST", data=payload, description="submit EO search (button)", url=target_url)
        except Exception as exc:
            logger.error(f"Search postback failed: {exc}")
            return None

    def _scrape_single_eo(
        self,
        eo_number: str,
        scraper_run_id: Optional[int] = None,
        start_page: int = 1,
    ) -> Dict:
        """Scrape one EO using HTTP pagination."""
        progress = self._load_progress(eo_number)
        self.pagination_target = None
        self.results_table_id = RESULTS_TABLE_ID
        resume_page = start_page
        # Prefer persisted EOProgress resume state
        if progress.status in ("partial", "failed") and progress.last_page >= 1:
            resume_page = max(start_page, progress.last_page + 1)
        logger.info(
            f"[DEBUG] Resume info for {eo_number}: start_page={start_page}, "
            f"eo_progress_last_page={progress.last_page}, eo_progress_status={progress.status}, "
            f"computed_resume_page={resume_page}"
        )

        try:
            soup = self._request("GET", description="load base page")
        except Exception as exc:
            return {"status": "failed", "error": f"initial GET failed: {exc}"}

        viewstate_present = soup.find("input", {"name": "__VIEWSTATE"}) is not None
        event_validation_present = soup.find("input", {"name": "__EVENTVALIDATION"}) is not None
        viewstate_gen_present = soup.find("input", {"name": "__VIEWSTATEGENERATOR"}) is not None
        logger.info(
            f"[DEBUG] Initial GET status={self._last_response_status} viewstate={viewstate_present} "
            f"eventvalidation={event_validation_present} viewstategen={viewstate_gen_present}"
        )

        soup = self._activate_eo_tab(soup)
        self._log_form_diagnostics(soup)
        soup = self._select_eo(soup, eo_number)
        if not soup:
            progress.mark_failed("EO selection failed")
            self._dump_debug_html(eo_number, "eo_selection_failed", soup or BeautifulSoup("", "lxml"))
            return {"status": "failed", "error": "EO selection failed"}

        if eo_number in soup.get_text():
            logger.info(f"[DEBUG] EO {eo_number} appears in page after selection")
        else:
            logger.warning(f"[DEBUG] EO {eo_number} not clearly visible after selection; continuing")

        soup = self._activate_eo_tab(soup)
        self._log_form_diagnostics(soup)
        soup = self._submit_search(soup)
        if not soup:
            self._dump_debug_html(eo_number, "search_postback_failed", soup or BeautifulSoup("", "lxml"))
            progress.mark_failed("Search postback failed")
            return {"status": "failed", "error": "search postback failed"}

        table = self._find_results_table(soup)
        if not table:
            logger.warning(f"[DEBUG] Results table not found after submitting search for EO {eo_number}")
            logger.warning(f"[DEBUG] Page snippet: {self._last_response_snippet}")
            self._dump_debug_html(eo_number, "no_table_after_search", soup)
            progress.mark_success(expected_pages=0, expected_rows=0)
            return {"status": "no_results", "created": 0, "updated": 0, "scraped_rows": 0}
        else:
            logger.info(f"[DEBUG] Results table detected with id={table.get('id')}")

        self._derive_pagination_target(soup)
        logger.info(f"[DEBUG] Pagination target={self.pagination_target}, current_page={self._current_page(soup)}, max_visible={self._max_visible_page(soup)}")

        # Jump directly to resume page if needed
        current_page = 1
        if resume_page > 1:
            logger.info(f"Resuming EO {eo_number}; attempting fast-forward to page {resume_page}")
            current_page = self._current_page(soup)

            # First try a single direct jump to the resume page
            direct_jump = self._goto_page(soup, resume_page)
            if direct_jump and not self._is_error_page(direct_jump):
                soup = direct_jump
                current_page = self._current_page(soup) or resume_page
                logger.info(f"[DEBUG] Direct resume jump landed on page {current_page} for EO {eo_number} (max_visible={self._max_visible_page(soup)})")
            else:
                logger.warning(f"[DEBUG] Direct resume jump to page {resume_page} failed; falling back to incremental fast-forward")

            def fast_forward(soup_obj, current, target):
                """Use visible pager jumps to reduce one-by-one navigation."""
                attempts = 0
                while current < target and attempts < 200:
                    if self._stop_requested(scraper_run_id):
                        logger.info(f"Stop requested during fast-forward at page {current} for EO {eo_number}")
                        progress.mark_partial(
                            last_page=current - 1 if current > 1 else 0,
                            scraped_rows=0,
                            error_msg="stop requested",
                            expected_pages=None,
                            expected_rows=None,
                        )
                        return soup_obj, current, True
                    attempts += 1
                    max_visible = self._max_visible_page(soup_obj) or current
                    logger.info(f"[DEBUG] Fast-forward state: current={current}, target={target}, max_visible={max_visible}")
                    # If target is within visible range, jump straight
                    if target <= max_visible:
                        next_page = target
                    else:
                        # jump to the last visible page to advance blocks
                        next_page = max_visible
                        if next_page == current:
                            next_page = current + 1

                    soup_next = self._goto_page(soup_obj, next_page)
                    if soup_next:
                        logger.info(f"[DEBUG] Jumped to page {next_page}; current_page_detected={self._current_page(soup_next)}, max_visible={self._max_visible_page(soup_next)}")
                    if not soup_next or self._is_error_page(soup_next):
                        logger.warning(f"Fast-forward jump to page {next_page} failed (current {current}, target {target})")
                        return soup_obj, current, False

                    current = self._current_page(soup_next) or next_page
                    max_visible_now = self._clamp_pages(current, self._max_visible_page(soup_next))
                    soup_obj = soup_next
                    if current % 50 == 0:
                        time.sleep(1)
                    else:
                        time.sleep(0.2)

                return soup_obj, current, False

            soup, current_page, stopped_ff = fast_forward(soup, current_page, resume_page)
            if stopped_ff:
                return {
                    "status": "stopped",
                    "created": 0,
                    "updated": 0,
                    "skipped_duplicates": 0,
                    "scraped_rows": 0,
                    "expected_pages": progress.expected_pages,
                    "expected_rows": progress.expected_rows,
                }
            if current_page < resume_page:
                logger.warning(f"Fast-forward could not reach resume page {resume_page}; continuing from page {current_page}")

        total_created = 0
        total_updated = 0
        total_rows_seen = 0
        total_skipped = 0
        max_page_seen = self._clamp_pages(current_page, self._max_visible_page(soup)) or current_page
        rows_per_page = None

        while True:
            if self._stop_requested(scraper_run_id):
                logger.info(f"Stop requested while processing EO {eo_number}")
                progress.mark_partial(
                    last_page=current_page - 1,
                    scraped_rows=total_rows_seen,
                    error_msg="stop requested",
                    expected_pages=max_page_seen,
                )
                return {"status": "stopped", "created": total_created, "updated": total_updated}

            rows = self._parse_table_rows(soup, eo_number)
            if (not rows and not self._find_results_table(soup)) or self._is_error_page(soup):
                logger.warning(f"[DEBUG] Results table missing on page {current_page} for EO {eo_number}")
                self._dump_debug_html(eo_number, f"missing_table_page_{current_page}", soup)
                recovered = self._recover_page(eo_number, current_page)
                if recovered and not self._is_error_page(recovered) and self._find_results_table(recovered):
                    logger.info(f"[DEBUG] Recovered session for EO {eo_number} page {current_page}")
                    soup = recovered
                    rows = self._parse_table_rows(soup, eo_number)
                else:
                    progress.mark_partial(
                        last_page=current_page - 1,
                        scraped_rows=total_rows_seen,
                        error_msg="table missing during pagination",
                        expected_pages=max_page_seen,
                        expected_rows=progress.expected_rows,
                    )
                    return {
                        "status": "partial",
                        "created": total_created,
                        "updated": total_updated,
                        "skipped_duplicates": total_skipped,
                        "scraped_rows": total_rows_seen,
                        "expected_pages": max_page_seen,
                        "expected_rows": progress.expected_rows,
                        "error": "table missing during pagination",
                    }
            rows_per_page = rows_per_page or (len(rows) if rows else None)
            page_result = self._persist_page(eo_number, rows, current_page)

            total_created += page_result.inserted
            total_updated += page_result.updated
            total_rows_seen += page_result.attempted
            total_skipped += page_result.skipped
            max_page_seen = self._clamp_pages(current_page, max(max_page_seen or current_page, self._max_visible_page(soup) or current_page))

            progress.last_page = current_page
            progress.scraped_rows = total_rows_seen
            progress.expected_pages = max_page_seen
            progress.expected_rows = (
                (rows_per_page or 0) * max_page_seen if rows_per_page is not None else progress.expected_rows
            )
            progress.status = "partial"
            progress.last_error = None
            progress.save(update_fields=["last_page", "scraped_rows", "expected_pages", "expected_rows", "status", "updated_at"])

            if self.pages_per_eo and current_page >= self.pages_per_eo:
                logger.warning(f"Reached safety page limit ({self.pages_per_eo}) for EO {eo_number}")
                progress.mark_partial(
                    last_page=current_page,
                    scraped_rows=total_rows_seen,
                    error_msg="page limit reached",
                    expected_pages=max_page_seen,
                    expected_rows=progress.expected_rows,
                )
                return {
                    "status": "partial",
                    "created": total_created,
                    "updated": total_updated,
                    "skipped_duplicates": total_skipped,
                    "scraped_rows": total_rows_seen,
                    "expected_pages": max_page_seen,
                    "expected_rows": progress.expected_rows,
                    "error": "page limit reached",
                }

            next_argument = self._next_page_argument(soup, current_page)
            if not next_argument:
                # No next link visible; treat current page as the last page we know
                max_page_seen = max(
                    max_page_seen or 1,
                    self._max_visible_page(soup) or current_page,
                    current_page,
                )
                progress.expected_pages = max_page_seen
                break

            next_page = current_page + 1
            soup = self._goto_page(soup, next_page)
            if not soup:
                progress.mark_partial(
                    last_page=current_page,
                    scraped_rows=total_rows_seen,
                    error_msg=f"pagination failed at page {next_page}",
                    expected_pages=max_page_seen,
                    expected_rows=progress.expected_rows,
                )
                return {
                    "status": "partial",
                    "created": total_created,
                    "updated": total_updated,
                    "skipped_duplicates": total_skipped,
                    "scraped_rows": total_rows_seen,
                    "expected_pages": max_page_seen,
                    "expected_rows": progress.expected_rows,
                    "error": f"pagination failed at page {next_page}",
                }

            new_page_num = self._current_page(soup)
            if new_page_num == current_page:
                logger.warning(f"[DEBUG] Pagination did not advance from page {current_page} for EO {eo_number}")
                self._dump_debug_html(eo_number, f"pagination_stuck_{current_page}", soup)
                break

            current_page = next_page
            if current_page % 50 == 0:
                time.sleep(1)
            else:
                time.sleep(0.3)  # Be gentle to the server

        progress.mark_success(expected_pages=max_page_seen, expected_rows=progress.expected_rows or total_rows_seen)

        return {
            "status": "success",
            "created": total_created,
            "updated": total_updated,
            "skipped_duplicates": total_skipped,
            "scraped_rows": total_rows_seen,
            "expected_pages": max_page_seen,
            "expected_rows": progress.expected_rows or total_rows_seen,
        }

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def scrape_by_eo_numbers(self, eo_numbers: List[str] = None, scraper_run_id: Optional[int] = None) -> Dict[str, int]:
        """
        Public entry point used by Celery tasks and the management command.
        """
        stats = {
            "total_eos": 0,
            "successful_eos": 0,
            "failed_eos": 0,
            "no_results_eos": 0,
            "partial_eos": 0,
            "total_converters": 0,
            "created": 0,
            "updated": 0,
            "skipped_duplicates": 0,
            "successful_eo_list": [],
            "failed_eo_list": [],
            "no_results_eo_list": [],
            "partial_eo_list": [],
            "verification": {
                "per_eo": [],
                "target": TARGET_TOTAL_ROWS,
                "total_scraped": 0,
                "delta_remaining": TARGET_TOTAL_ROWS,
                "partial_eos": [],
                "missing_pages": [],
            },
            "stopped": False,
        }

        try:
            self._setup_driver()
            if eo_numbers is None:
                eo_numbers = self.extract_eo_numbers()

            stats["total_eos"] = len(eo_numbers)
            logger.info("=" * 60)
            logger.info(f"STARTING HTTP EO SCRAPE FOR {stats['total_eos']} EO NUMBERS")
            if self.pages_per_eo:
                logger.info(f"Safety cap: {self.pages_per_eo} pages per EO")
            logger.info("=" * 60)

            for idx, eo_number in enumerate(eo_numbers, 1):
                logger.info(f"[{idx}/{stats['total_eos']}] EO {eo_number}")
                result = self._scrape_single_eo(eo_number, scraper_run_id=scraper_run_id, start_page=1)
                status = result.get("status")

                if status == "success":
                    stats["successful_eos"] += 1
                    stats["successful_eo_list"].append(eo_number)
                elif status == "no_results":
                    stats["no_results_eos"] += 1
                    stats["no_results_eo_list"].append(eo_number)
                elif status == "partial":
                    stats["partial_eos"] += 1
                    stats["partial_eo_list"].append(eo_number)
                elif status == "stopped":
                    stats["stopped"] = True
                    break
                else:
                    stats["failed_eos"] += 1
                    stats["failed_eo_list"].append(eo_number)

                created = result.get("created", 0)
                updated = result.get("updated", 0)
                skipped = result.get("skipped_duplicates", 0)
                scraped_rows = result.get("scraped_rows", created + updated)
                stats["created"] += created
                stats["updated"] += updated
                stats["skipped_duplicates"] += skipped
                stats["total_converters"] += scraped_rows

                stats["verification"]["per_eo"].append({
                    "eo_number": eo_number,
                    "expected_rows": result.get("expected_rows"),
                    "scraped_rows": scraped_rows,
                    "status": status,
                    "expected_pages": result.get("expected_pages"),
                })

                if status == "partial":
                    stats["verification"]["partial_eos"].append(eo_number)

                if scraper_run_id:
                    try:
                        scraper_run = ScraperRun.objects.get(id=scraper_run_id)
                        scraper_run.current_eo_number = eo_number
                        scraper_run.current_page_number = 1
                        scraper_run.processed_count = stats["successful_eos"] + stats["failed_eos"] + stats["no_results_eos"] + stats["partial_eos"]
                        scraper_run.success_count = stats["successful_eos"]
                        scraper_run.failed_count = stats["failed_eos"]
                        scraper_run.no_results_count = stats["no_results_eos"]
                        scraper_run.partial_count = stats["partial_eos"]
                        if eo_number not in scraper_run.eo_numbers_processed:
                            scraper_run.eo_numbers_processed.append(eo_number)
                        if status == "failed" and eo_number not in scraper_run.eo_numbers_failed:
                            scraper_run.eo_numbers_failed.append(eo_number)
                        scraper_run.save()
                    except ScraperRun.DoesNotExist:
                        pass

            # Verification log
            stats["verification"]["total_scraped"] = stats["total_converters"]
            stats["verification"]["delta_remaining"] = max(
                0, stats["verification"]["target"] - stats["verification"]["total_scraped"]
            )

            logger.info("=" * 60)
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
            logger.info(
                f"Verification → total_scraped={stats['verification']['total_scraped']} "
                f"target={stats['verification']['target']} "
                f"delta_remaining={stats['verification']['delta_remaining']}"
            )
            if stats["verification"]["partial_eos"]:
                logger.info(f"Partial EOs: {', '.join(stats['verification']['partial_eos'][:20])}")

        except Exception as exc:
            logger.error(f"Critical error during scraping: {exc}", exc_info=True)
        finally:
            self._close_driver()

        return stats
