# EO Scraper Pagination Fix - Test Version

## Problem

The original EO scraper (`eo_scraper.py`) has a hard limit on pagination that prevents it from scraping all available pages for each Executive Order number.

### Root Cause

In `eo_scraper.py`, the `_extract_multiple_pages()` method (lines 385-424):

```python
def _extract_multiple_pages(self, eo_number: str) -> List[Dict]:
    all_converters = []
    page_num = 1

    logger.info(f"Extracting up to {self.pages_per_eo} pages for {eo_number}")

    while page_num <= self.pages_per_eo:  # ❌ HARD LIMIT HERE
        logger.info(f"Processing page {page_num} for {eo_number}")
        page_converters = self._extract_page_data(eo_number)

        if not page_converters:
            break

        all_converters.extend(page_converters)

        # Only tries pagination if under limit
        if page_num < self.pages_per_eo:  # ❌ STOPS PAGINATION EARLY
            if self._click_next_results_page():
                page_num += 1
            else:
                break
        else:
            logger.info(f"Reached maximum pages ({self.pages_per_eo})")
            break

    return all_converters
```

**Issues:**
1. Line 400: `while page_num <= self.pages_per_eo` - Stops after hitting the configured limit
2. Line 413: `if page_num < self.pages_per_eo` - Never attempts to paginate on the last allowed page
3. Default `pages_per_eo=3` means it only scrapes 3 pages even if 10+ pages exist

## Solution

The test version (`eo_scraper_test.py`) implements:

### 1. Auto-Pagination Until Exhausted

```python
def _extract_multiple_pages(self, eo_number: str) -> List[Dict]:
    all_converters = []
    page_num = 1

    if self.pages_per_eo:
        logger.info(f"Extracting pages for {eo_number} (max limit: {self.pages_per_eo})")
    else:
        logger.info(f"Extracting all available pages for {eo_number} (no limit)")

    # ✅ Continue scraping until we run out of pages OR hit optional safety limit
    while True:
        logger.info(f"Processing page {page_num} for {eo_number}")

        page_converters = self._extract_page_data(eo_number)

        if not page_converters:
            logger.info(f"No data on page {page_num}, stopping pagination")
            break

        all_converters.extend(page_converters)
        logger.info(f"Total so far: {len(all_converters)} converters")

        # ✅ Check optional safety limit (not a hard requirement)
        if self.pages_per_eo and page_num >= self.pages_per_eo:
            logger.info(f"Reached safety limit of {self.pages_per_eo} pages")
            break

        # ✅ Always try to go to next page until it fails
        if self._click_next_results_page():
            page_num += 1
        else:
            logger.info("No more pages available, pagination complete")
            break

    logger.info(f"✓ Total converters extracted for {eo_number}: {len(all_converters)} across {page_num} pages")
    return all_converters
```

### 2. Optional Safety Limit (Instead of Hard Limit)

```python
def __init__(self, headless: bool = True, timeout: int = 20, pages_per_eo: Optional[int] = None):
    """
    Args:
        pages_per_eo: Maximum pages to scrape per EO (None or 0 = unlimited, scrape all available pages)
    """
    self.pages_per_eo = pages_per_eo if pages_per_eo else None
```

- `pages_per_eo=None` or `0` → Scrape ALL pages
- `pages_per_eo=5` → Safety limit of 5 pages (useful for testing/avoiding infinite loops)

### 3. Enhanced Numbered Pagination with Ellipsis Support

```python
def _click_next_results_page(self, current_page: Optional[int] = None) -> bool:
    """
    Click the next numbered page button in pagination.
    CARB uses numbered pagination (1, 2, 3...) instead of Next/Previous buttons.
    """
    # Try to find numbered page button (e.g., page 11)
    next_page = current_page + 1
    next_page_xpath = f"//table[@id='...']//tr[last()]//a[normalize-space(text())='{next_page}']"

    try:
        next_page_button = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, next_page_xpath))
        )
        # Scroll to make visible
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page_button)

    except TimeoutException:
        # ✅ Page button not found - try clicking ellipsis (...) to reveal more pages
        logger.info(f"Page {next_page} button not visible, looking for ellipsis (...)")

        ellipsis_xpath = "//table[@id='...']//tr[last()]//a[normalize-space(text())='...']"
        try:
            ellipsis_button = self.driver.find_element(By.XPATH, ellipsis_xpath)
            logger.info(f"Found ellipsis (...), clicking to reveal more pages")
            self.driver.execute_script("arguments[0].click();", ellipsis_button)
            time.sleep(2)

            # ✅ Try to find the page button again after clicking ellipsis
            try:
                next_page_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, next_page_xpath))
                )
            except TimeoutException:
                next_page_button = None
        except NoSuchElementException:
            next_page_button = None

        # ✅ If still not found, look for Next (>) button as fallback
        if next_page_button is None:
            # Try alternative selectors...
            return False

    # Click the button and handle postback...
    # ✅ IMPORTANT: Click EO Search tab again after pagination
    eo_tab = WebDriverWait(self.driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "EO Search"))
    )
    self.driver.execute_script("arguments[0].click();", eo_tab)

    return True
```

## Testing

### Test Command

Use the new test management command:

```bash
# Test with first 3 EO numbers, scrape ALL pages per EO
python manage.py scrape_by_eo_test --test --headless

# Test with first 3 EO numbers, safety limit of 5 pages per EO
python manage.py scrape_by_eo_test --test --pages=5 --headless

# Test specific EO number, scrape all pages
python manage.py scrape_by_eo_test --eo-numbers=D-393-143 --headless

# Test with visible browser (for debugging)
python manage.py scrape_by_eo_test --test --visible
```

### Expected Behavior

**Before (Original Scraper):**
```
Extracting up to 3 pages for D-393-143
Processing page 1 for D-393-143
Found 10 rows on current page
Processing page 2 for D-393-143
Found 10 rows on current page
Processing page 3 for D-393-143
Found 10 rows on current page
Reached maximum pages (3)
✓ Total converters extracted for D-393-143: 30
```
→ Stops at page 3 even if more pages exist!

**After (Test Version with no limit):**
```
Extracting all available pages for D-393-143 (no limit)
Processing page 1 for D-393-143
Found 10 rows on current page
Total so far: 10 converters
Processing page 2 for D-393-143
Found 10 rows on current page
Total so far: 20 converters
Processing page 3 for D-393-143
Found 10 rows on current page
Total so far: 30 converters
Processing page 4 for D-393-143
Found 10 rows on current page
Total so far: 40 converters
Processing page 5 for D-393-143
Found 8 rows on current page
Total so far: 48 converters
No enabled Next pagination control found, no more pages
No more pages available, pagination complete
✓ Total converters extracted for D-393-143: 48 across 5 pages
```
→ Continues until no "Next" button exists!

## Files Created

1. **`converters/eo_scraper_test.py`** - Test version of scraper with pagination fix
2. **`converters/management/commands/scrape_by_eo_test.py`** - Test management command
3. **`PAGINATION_FIX_README.md`** - This documentation

## Next Steps

After testing and verifying the fix works correctly:

1. Apply the same changes to the original `eo_scraper.py`
2. Update the original `scrape_by_eo.py` command to support `--pages=0` for unlimited
3. Update the admin dashboard to allow users to choose "scrape all pages"

## Key Changes Summary

| Aspect | Original | Test Version |
|--------|----------|--------------|
| Default behavior | Stop at page 3 | Scrape all pages |
| pages_per_eo | Required (default=3) | Optional (default=None) |
| Loop condition | `while page_num <= limit` | `while True` with smart breaks |
| Pagination check | Only if `page_num < limit` | Always attempt until fails |
| Next button detection | Basic | Enhanced (checks disabled state) |
| Logging | Pages "up to X" | "all available" or "max limit X" |
