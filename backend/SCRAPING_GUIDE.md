# CARB Data Scraping Guide

This project supports **two methods** for scraping CARB catalytic converter data:

1. **PDF Scraping** (Recommended) - Fast, reliable, complete historical data
2. **Website Scraping** - Live data from the interactive CARB website

---

## Method 1: PDF Scraping (Recommended)

### Overview
Scrapes data from the CARB PDF file containing exempt catalytic converters.

### Advantages
- ✅ Fast and efficient
- ✅ Complete historical data
- ✅ No browser automation required
- ✅ Works offline with local PDF
- ✅ Already tested and working

### Usage

#### Basic Usage (Uses local PDF)
```bash
cd backend
python manage.py scrape_carb_data
```

#### Download from Remote URL
```bash
python manage.py scrape_carb_data --remote
```

#### Limit Records (for testing)
```bash
python manage.py scrape_carb_data --limit 100
```

### Data Source
- **Local PDF**: `backend/data/Data.pdf` (included in project)
- **Remote PDF**: https://ww2.arb.ca.gov/sites/default/files/aftermarket/aftermktcat/exemptcat09.pdf

---

## Method 2: Website Scraping

### Overview
Scrapes live data from the interactive CARB website using Selenium browser automation.

### Advantages
- ✅ Most up-to-date data
- ✅ Can scrape specific manufacturers
- ✅ Access to live database

### Disadvantages
- ⚠️ Slower (requires browser automation)
- ⚠️ Requires Chrome/Chromium + ChromeDriver
- ⚠️ More complex setup
- ⚠️ Subject to website changes

### Prerequisites

Install Selenium and ChromeDriver:

```bash
# Install Selenium
pip install selenium

# Install ChromeDriver
# macOS:
brew install chromedriver

# Ubuntu/Debian:
sudo apt-get install chromium-chromedriver

# Or download from: https://chromedriver.chromium.org/
```

### Usage

#### Test Mode (2 manufacturers only)
```bash
cd backend
python manage.py scrape_website --test
```

#### Scrape All Manufacturers
```bash
python manage.py scrape_website
```

#### Scrape with Browser Visible (for debugging)
```bash
python manage.py scrape_website --no-headless
```

#### Limit Number of Manufacturers
```bash
python manage.py scrape_website --limit 10
```

#### Custom Timeout
```bash
python manage.py scrape_website --timeout 15
```

### Data Source
- **Website**: https://ssl.arb.ca.gov/AftermarketParts/catalysts

---

## Comparison

| Feature | PDF Scraping | Website Scraping |
|---------|-------------|------------------|
| Speed | ⚡ Very Fast | 🐢 Slower |
| Setup | ✅ Simple | ⚠️ Complex |
| Data Freshness | 📅 Historical | 🔄 Live |
| Reliability | ✅ High | ⚠️ Medium |
| Browser Required | ❌ No | ✅ Yes |
| Offline Support | ✅ Yes | ❌ No |
| Recommendation | ✅ Recommended | 🔬 Advanced Use |

---

## Combined Workflow

You can use both methods together for comprehensive data coverage:

```bash
# 1. Initial data load from PDF (fast, complete)
python manage.py scrape_carb_data

# 2. Update with latest data from website (optional)
python manage.py scrape_website --limit 5

# 3. Verify data
python manage.py shell
>>> from converters.models import CatalyticConverter
>>> print(f"Total converters: {CatalyticConverter.objects.count()}")
```

---

## Troubleshooting

### PDF Scraping Issues

**Issue**: "File not found" error
```bash
# Solution: Ensure PDF exists
ls backend/data/Data.pdf

# Or use remote download
python manage.py scrape_carb_data --remote
```

### Website Scraping Issues

**Issue**: "ChromeDriver not found"
```bash
# Solution: Install ChromeDriver
brew install chromedriver  # macOS
# or
sudo apt-get install chromium-chromedriver  # Linux
```

**Issue**: "Chrome version mismatch"
```bash
# Solution: Update ChromeDriver to match your Chrome version
# Download from: https://chromedriver.chromium.org/
```

**Issue**: "Timeout waiting for elements"
```bash
# Solution: Increase timeout
python manage.py scrape_website --timeout 20
```

**Issue**: "No data found"
```bash
# Solution: Website structure may have changed
# Run in visible mode to debug:
python manage.py scrape_website --test --no-headless
```

---

## Data Management

### Clear All Data
```bash
python manage.py clear_data
```

### View Statistics
```bash
python manage.py shell
>>> from converters.models import Manufacturer, CatalyticConverter
>>> print(f"Manufacturers: {Manufacturer.objects.count()}")
>>> print(f"Converters: {CatalyticConverter.objects.count()}")
```

### Export Data
```bash
python manage.py dumpdata converters > backup.json
```

---

## Performance Tips

1. **For Initial Setup**: Use PDF scraping (faster)
2. **For Updates**: Use website scraping with `--limit` flag
3. **For Testing**: Always use `--test` flag first
4. **For Production**: Schedule PDF scraping daily/weekly

---

## API Endpoints

After scraping, data is available via REST API:

```bash
# Get all converters
curl http://localhost:8000/api/converters/

# Search converters
curl http://localhost:8000/api/converters/search/?year=2015&make=Honda

# Get filter options
curl http://localhost:8000/api/converters/search-options/
```

---

## Support

For issues or questions:
- Check this guide first
- Review logs in the console output
- Test with `--test` flag before full scraping
- Ensure all prerequisites are installed
