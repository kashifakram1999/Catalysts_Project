# CARB Scraper Capabilities (2025)

This project maintains **two complementary scraping pipelines** so you can seed and refresh the catalytic converter database from either the official CARB PDF catalog or the interactive website. Both pipelines plug directly into the Django management-command layer, so you can run them from the CLI or schedule them with cron/CI.

---

## 1. PDF Scraper (Fast & Deterministic)

- **Code**: `backend/converters/scraper.py` (`CARBScraper.scrape_pdf`)
- **Command**: `python manage.py scrape_carb_data --source=pdf`
- **Data source**: `backend/data/Data.pdf` (local copy) or CARB-hosted PDF (`https://ww2.arb.ca.gov/.../exemptcat09.pdf`)
- **Best for**: Initial data loads, bulk refreshes, automated jobs, or environments without a browser.

### Why use it
- Runs in seconds and does not require Selenium/Chrome
- Works offline when `Data.pdf` is present
- Produces the most complete historical snapshot available in the PDF

### Flags
- `--remote` – download the PDF on demand instead of using the local file
- `--limit N` – keep only the first N parsed rows (useful for smoke tests)
- `--source both` – run PDF + website scraping in one shot (see below)

### Typical workflow
```bash
cd backend
python manage.py scrape_carb_data --source=pdf        # default
python manage.py scrape_carb_data --source=pdf --remote
python manage.py scrape_carb_data --source=pdf --limit 100
```

---

## 2. Website Scraper (Live CARB Portal)

- **Code**: `backend/converters/website_scraper.py` (`CARBWebsiteScraper`)
- **Command**: `python manage.py scrape_website`
- **Data source**: https://ssl.arb.ca.gov/AftermarketParts/catalysts (Selenium-driven)
- **Best for**: Pulling the latest approvals or validating manufacturers/models that may not yet be in the PDF.

### Why use it
- Walks the ASP.NET AJAX UI like a human (select make → year → model → engine size → search)
- Handles pagination and extracts EO numbers, part numbers, test groups, application types, etc.
- Can limit to a subset of manufacturers while testing.

### Flags
- `--headless / --no-headless` – run Chrome invisibly (default) or with UI for debugging
- `--limit N` – cap the number of manufacturers scraped
- `--test` – shortcut that sets `--limit 2` and prints a reminder that you are in test mode
- `--timeout 15` – adjust Selenium waits for slower connections

### Typical workflow
```bash
cd backend
python manage.py scrape_website --test                  # fast smoke test
python manage.py scrape_website --limit 10              # sample subset
python manage.py scrape_website --no-headless --limit 1 # debug flow in a visible browser
python manage.py scrape_website                         # full run
```

> **Prereqs**: Chrome/Chromium + matching ChromeDriver available on PATH. Use `backend/verify_selenium_setup.py` if you need to confirm the environment.

---

## Combined Command (`scrape_carb_data`)

`python manage.py scrape_carb_data` is the single entry point that can orchestrate both PDF and website scraping:

| Flag | Purpose |
| --- | --- |
| `--source pdf` (default) | PDF only |
| `--source website` | Website only (headless Selenium) |
| `--source both` | Run PDF first, then website data, merging results |
| `--limit N` | Stop after N records (applied after combining results) |
| `--remote` | Force remote PDF download |

Example:

```bash
# Hybrid run: download fresh PDF AND scrape a few live manufacturers
python manage.py scrape_carb_data --source=both --remote --limit 500
```

The command pipes every record through `CARBDataProcessor` to normalize fields, then upserts `Manufacturer` and `CatalyticConverter` rows. `last_scraped` is set automatically so you can track freshness.

---

## Supporting Assets

- `backend/data/README.md` – explains how local PDFs are stored/used
- `backend/SCRAPING_GUIDE.md` – deeper dive (troubleshooting, ChromeDriver notes, etc.)
- `backend/test_scraper.py` – quick connectivity checks
- `backend/verify_selenium_setup.py` – confirms Selenium + ChromeDriver installation
- `backend/converters/management/commands/clear_data.py` – wipes converters/manufacturers when you need a clean slate (use carefully)

---

## Choosing the Right Pipeline

| Scenario | Recommended Command |
| --- | --- |
| Initial database load | `python manage.py scrape_carb_data --source=pdf`
| Quick sanity check | `python manage.py scrape_carb_data --source=pdf --limit 50`
| Need freshest EO updates | `python manage.py scrape_website --limit 5` or `--source=both`
| Debug Selenium flow | `python manage.py scrape_website --no-headless --limit 1`
| Scheduled weekly refresh | `python manage.py scrape_carb_data --source=pdf` (cron/CI)

Keeping both approaches ensures resiliency: if CARB updates the PDF slowly, you still have the live portal; if the website changes layout, the PDF pipeline keeps you covered.

Happy scraping! 🧪
