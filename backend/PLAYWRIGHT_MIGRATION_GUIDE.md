# Playwright Migration - Fix Guide

## Current Issues & Solutions

### Issue 1: Still Using Selenium (chromedriver error)
**Problem**: The error shows `chromedriver` stack traces, meaning Celery workers are still running the old Selenium code.

**Solution**: Restart Celery workers to load the new Playwright code.

### Issue 2: Parallel Workers Not Starting
**Problem**: Playwright initialization error `'options'` in forked worker processes.

**Solution**: Applied fixes to handle multiprocessing correctly.

---

## Steps to Fix Both Issues

### Step 1: Commit Your Changes
```bash
cd /Users/muhmmadkashif/Documents/GitHub/Catalysts_Project/backend

# Check what's changed
git status

# Add all Playwright migration files
git add converters/eo_scraper_playwright.py
git add converters/tasks.py
git add converters/models.py
git add converters/migrations/0007_*.py
git add converters/admin.py
git add requirements.txt

# Commit
git commit -m "Complete Selenium to Playwright migration with parallel worker support"
```

### Step 2: Stop All Running Celery Workers
```bash
# Find all running Celery processes
ps aux | grep celery

# Kill them (replace PID with actual process IDs)
pkill -f celery

# Or use this to kill all celery processes:
killall -9 celery
```

### Step 3: Restart Celery Workers
```bash
cd /Users/muhmmadkashif/Documents/GitHub/Catalysts_Project/backend

# Make sure PostgreSQL is running
# brew services start postgresql

# Activate virtual environment
source venv/bin/activate

# Start Celery with proper pool type for Mac OS
# IMPORTANT: Use 'solo' or 'threads' pool instead of 'fork' for Playwright compatibility
celery -A carb_backend worker --pool=solo --loglevel=info

# OR for parallel processing (use threads instead of fork):
celery -A carb_backend worker --pool=threads --concurrency=4 --loglevel=info
```

### Step 4: Verify Playwright is Running

In the Celery logs, you should see:
- ✅ `Using explicit headless shell: .../chromium_headless_shell-1200/...`
- ✅ `Playwright browser initialized successfully`
- ❌ NOT `chromedriver` or Selenium references

### Step 5: Test Single Worker Scraping
```bash
# In a new terminal, activate virtualenv
cd /Users/muhmmadkashif/Documents/GitHub/Catalysts_Project/backend
source venv/bin/activate

# Run Django shell
python manage.py shell

# Test scraping
from converters.tasks import scrape_website_task
result = scrape_website_task.delay(headless=True, test_mode=True, pages=5)

# Check status
result.ready()  # Returns True when done
result.result   # Get results

# Check ScraperRun in admin
# http://localhost:8000/admin/converters/scraperrun/
```

### Step 6: Test Parallel Scraping (PostgreSQL Required)
```bash
# In Django shell
from converters.tasks import parallel_scrape_website
result = parallel_scrape_website.delay(
    num_workers=4,
    headless=True,
    pages=50,
    test_mode=True
)

# Monitor progress
result.ready()
result.result
```

---

## Troubleshooting

### If you still see chromedriver errors:
1. Make sure you killed ALL celery processes: `pkill -f celery`
2. Verify no celery processes running: `ps aux | grep celery`
3. Restart celery fresh
4. Check that tasks.py imports `CARBPlaywrightScraper`, not `CARBSeleniumScraper`

### If parallel workers fail with "'options'" error:
1. Use `--pool=solo` or `--pool=threads` instead of default fork pool
2. Check Playwright is installed in virtualenv: `pip show playwright`
3. Verify chromium installed: `ls ~/Library/Caches/ms-playwright/`

### If timeout on page 354:
This was happening with Selenium. Playwright handles pagination better, but:
- Increase timeout if needed: `CARBPlaywrightScraper(timeout=60)`  # 60 seconds
- The scraper will retry and save partial results (8825 converters saved)
- Check `eo_failure_details` in ScraperRun admin for detailed error info

---

## Performance Tips

### For Mac OS M3 Max with 36GB RAM:
```bash
# Optimal Celery configuration
celery -A carb_backend worker \
  --pool=threads \
  --concurrency=8 \
  --max-tasks-per-child=50 \
  --loglevel=info

# This will:
# - Use 8 parallel threads (good for M3 Max)
# - Restart workers every 50 tasks (prevents memory leaks)
# - Use thread pool (works better with Playwright)
```

### For 900K+ Records:
```python
# Use parallel scraping with 8 workers
from converters.tasks import parallel_scrape_website
parallel_scrape_website.delay(
    num_workers=8,
    headless=True,
    pages=None,  # No limit, scrape all pages
    test_mode=False
)
```

---

## Key Differences: Selenium vs Playwright

| Feature | Selenium | Playwright |
|---------|----------|------------|
| Browser | chromedriver | chromium_headless_shell-1200 |
| Stability | Crashes on long runs | Stable for hours |
| Timeout Handling | Hard failures | Automatic retries |
| Failure Tracking | Silent failures | Detailed `eo_failure_details` |
| Pagination | Timeout on page 354 | Robust retry logic |
| Parallel Support | Fork pool OK | Thread pool required |

---

## Verification Checklist

- [ ] All Celery processes killed
- [ ] New Celery worker started with `--pool=solo` or `--pool=threads`
- [ ] Logs show "Playwright browser initialized successfully"
- [ ] Logs show chromium_headless_shell-1200 path
- [ ] NO chromedriver references in logs
- [ ] PostgreSQL database configured
- [ ] Test scraping completes successfully
- [ ] ScraperRun shows `engine_used='playwright'` in admin

---

## Quick Test Command

```bash
# Complete test workflow
cd /Users/muhmmadkashif/Documents/GitHub/Catalysts_Project/backend
pkill -f celery
celery -A carb_backend worker --pool=solo --loglevel=info &
sleep 5
python test_single_eo.py
```

Expected output:
```
✓ Browser initialized
✓ Created ScraperRun
✓ Success: 3
✗ Failed: 0
SUCCESS RATE: 100.0%
```
