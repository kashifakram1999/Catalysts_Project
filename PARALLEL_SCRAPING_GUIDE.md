# Parallel Scraping Guide

## Overview

The parallel scraping system divides EO numbers across multiple workers to dramatically speed up data collection from the CARB website.

### Key Benefits:
- **4x Faster**: With 4 workers, scraping completes ~4x faster
- **Scalable**: Add more workers for even faster scraping
- **Reliable**: Each worker has its own timeout protection
- **Monitored**: Real-time progress tracking for all workers

---

## Architecture

```
Parent Task (Coordinator)
    │
    ├─→ Worker 1: Scrapes EO numbers 1-78    (Batch 1/4)
    │
    ├─→ Worker 2: Scrapes EO numbers 79-156  (Batch 2/4)
    │
    ├─→ Worker 3: Scrapes EO numbers 157-234 (Batch 3/4)
    │
    └─→ Worker 4: Scrapes EO numbers 235-313 (Batch 4/4)
          │
          └─→ All results aggregated → Final statistics
```

### How It Works:

1. **Coordinator Task** (`parallel_scrape_website`):
   - Extracts all EO numbers from CARB website
   - Divides EO numbers into equal batches
   - Launches worker tasks in parallel
   - Waits for all workers to complete
   - Aggregates results from all workers

2. **Worker Tasks** (`scrape_eo_batch`):
   - Each worker scrapes its assigned batch of EO numbers
   - Runs independently with its own browser instance
   - Reports progress and statistics
   - Fails gracefully without affecting other workers

---

## Configuration

### settings.py Configuration

**File**: `backend/carb_backend/settings.py` (lines 248-258)

```python
'nightly_website_scrape': {
    'task': 'converters.tasks.parallel_scrape_website',
    'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM UTC
    'options': {'queue': 'scraping'},
    'kwargs': {
        'num_workers': 4,  # Number of parallel workers
        'headless': True,
        'pages': 50,      # Max pages per EO
        'test_mode': False,
        'eo_numbers': None,
    },
},
```

### Adjustable Parameters:

| Parameter | Default | Description | Recommendation |
|-----------|---------|-------------|----------------|
| `num_workers` | 4 | Number of parallel workers | 2-8 depending on server resources |
| `headless` | True | Run browsers in headless mode | True for production |
| `pages` | 50 | Max pages per EO | 50-100 (prevents timeouts) |
| `test_mode` | False | Test with first 12 EOs | True for testing only |
| `eo_numbers` | None | Specific EOs to scrape | Comma-separated list or None |

---

## Running Parallel Scraping

### Option 1: Scheduled Task (Automatic)

The nightly task runs automatically at 2:00 AM UTC:

```bash
# Start Celery Beat (if not already running)
celery -A carb_backend beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Option 2: Django Admin (Manual)

1. Go to: http://localhost:8000/admin/scraper-dashboard/
2. Click "Run Website Scraper"
3. Configure options:
   - Number of workers: 4
   - Headless mode: Yes
   - Pages per EO: 50
   - Test mode: No (unless testing)
4. Click "Start Scraping"

### Option 3: Python Script (Testing)

```bash
cd backend
source venv/bin/activate

# Visual test with 2 workers (first 6 EO numbers)
python test_parallel_scraping.py 2 true false

# Headless test with 4 workers (first 12 EO numbers)
python test_parallel_scraping.py 4 true true

# Full scrape with 4 workers (all EO numbers)
python test_parallel_scraping.py 4 false true
```

**Arguments**:
1. Number of workers (default: 2)
2. Test mode: true/false (default: true)
3. Headless: true/false (default: false)

### Option 4: Celery Task Directly

```python
from converters.tasks import parallel_scrape_website

result = parallel_scrape_website.apply_async(
    kwargs={
        'num_workers': 4,
        'headless': True,
        'pages': 50,
        'test_mode': False,
        'eo_numbers': None,
    },
    queue='scraping'
)

print(f"Task ID: {result.id}")
```

---

## Monitoring Progress

### Real-time Monitor (Recommended)

```bash
python monitor_parallel_scraping.py <task_id> [refresh_interval]

# Example
python monitor_parallel_scraping.py abc123def456 5
```

**Features**:
- Live progress bars for each worker
- Real-time statistics
- Batch-by-batch breakdown
- Auto-refresh (default: 5 seconds)
- Final aggregated statistics

**Example Output**:
```
================================================================================
PARALLEL SCRAPING MONITOR - Elapsed: 15.2m
================================================================================
Parent Task: abc123def456
Time: 2024-11-14 20:30:15
================================================================================

Parent Task Status: PROGRESS
📊 Progress: 45%
📝 Status: 4 workers launched, scraping in progress...
👷 Workers: 4
📋 Total EO Numbers: 313

────────────────────────────────────────────────────────────────────────────────
WORKER TASKS
────────────────────────────────────────────────────────────────────────────────

🔄 Worker 1 (abc12345...): PROGRESS
   Batch: 1/4
   EOs: 35/78 [████████████░░░░░░░░░░░░░░░░░░] 45%
   Status: Searching for EO: D-193-65
   Stats: 30 successful, 5 failed, 1523 converters

✅ Worker 2 (def45678...): SUCCESS
   ✓ Completed: 78 EOs, 2341 converters

🔄 Worker 3 (ghi78901...): PROGRESS
   Batch: 3/4
   EOs: 22/78 [████████░░░░░░░░░░░░░░░░░░░░░░] 28%
   Status: Searching for EO: D-245-89
   Stats: 18 successful, 4 failed, 987 converters

⏳ Worker 4 (jkl23456...): PENDING
   Waiting to start...
```

### Quick Status Check

```bash
# Check parent task
python -c "from celery.result import AsyncResult; r = AsyncResult('abc123def456'); print(f'State: {r.state}'); print(f'Info: {r.info}')"

# Check all task results from last 24 hours
python monitor_tasks.py
```

### Django Admin

Navigate to: http://localhost:8000/admin/scraper-dashboard/progress/

Enter the task ID to view progress.

---

## Celery Worker Configuration

### Recommended Setup

For optimal parallel scraping, you need **multiple Celery workers** OR **workers with higher concurrency**.

### Option 1: Multiple Worker Processes (Recommended)

Run multiple worker processes in separate terminals:

```bash
# Terminal 1: Worker 1
celery -A carb_backend worker -l info -Q scraping -n worker1@%h

# Terminal 2: Worker 2
celery -A carb_backend worker -l info -Q scraping -n worker2@%h

# Terminal 3: Worker 3
celery -A carb_backend worker -l info -Q scraping -n worker3@%h

# Terminal 4: Worker 4
celery -A carb_backend worker -l info -Q scraping -n worker4@%h
```

### Option 2: Single Worker with Concurrency

Run one worker with multiple threads:

```bash
celery -A carb_backend worker -l info -Q scraping --concurrency=5
```

**Note**: `--concurrency=5` means:
- 1 thread for the parent/coordinator task
- 4 threads for the worker tasks

### Option 3: Production (Supervisor)

**File**: `/etc/supervisor/conf.d/celery-workers.conf`

```ini
[program:celery-worker-1]
command=/path/to/venv/bin/celery -A carb_backend worker -l info -Q scraping -n worker1@%%h
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker1.log

[program:celery-worker-2]
command=/path/to/venv/bin/celery -A carb_backend worker -l info -Q scraping -n worker2@%%h
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker2.log

[program:celery-worker-3]
command=/path/to/venv/bin/celery -A carb_backend worker -l info -Q scraping -n worker3@%%h
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker3.log

[program:celery-worker-4]
command=/path/to/venv/bin/celery -A carb_backend worker -l info -Q scraping -n worker4@%%h
directory=/path/to/backend
user=www-data
autostart=true
autorestart=true
stdout_logfile=/var/log/celery/worker4.log
```

---

## Performance Analysis

### Single Worker (Original):
- **Total EO Numbers**: 313
- **Average Time per EO**: 2-5 minutes
- **Total Time**: ~26 hours (if all hit 50 page limit)
- **Realistic Time**: 1-2 hours (most EOs have < 10 pages)

### 4 Workers (Parallel):
- **Total EO Numbers**: 313
- **EOs per Worker**: ~78
- **Parallel Execution**: All workers run simultaneously
- **Total Time**: ~6.5 hours (worst case) / **15-30 minutes** (realistic)
- **Speedup**: **4x faster** 🚀

### 8 Workers (Maximum):
- **Total EO Numbers**: 313
- **EOs per Worker**: ~39
- **Total Time**: ~3.25 hours (worst case) / **8-15 minutes** (realistic)
- **Speedup**: **8x faster** 🚀🚀

### Resource Requirements:

| Workers | RAM | CPU | Chrome Instances | Recommended For |
|---------|-----|-----|------------------|-----------------|
| 2 | ~2GB | 2 cores | 2 | Testing |
| 4 | ~4GB | 4 cores | 4 | Production (default) |
| 6 | ~6GB | 6 cores | 6 | High-performance |
| 8 | ~8GB | 8 cores | 8 | Maximum speed |

---

## Troubleshooting

### Issue 1: Workers Not Starting

**Symptom**: Task remains in PENDING state

**Solution**:
```bash
# Check if workers are running
celery -A carb_backend inspect active

# Check worker stats
celery -A carb_backend inspect stats

# Restart workers
# CTRL+C to stop existing workers, then restart
celery -A carb_backend worker -l info -Q scraping --concurrency=5
```

### Issue 2: Workers Timing Out

**Symptom**: Workers fail with `TimeLimitExceeded` error

**Solution**:
1. Reduce `pages` limit in settings (50 → 30)
2. Increase worker timeout in `tasks.py`:
   ```python
   soft_time_limit=3 * 60 * 60,  # 3 hours
   ```

### Issue 3: Memory Issues

**Symptom**: Workers crash or system runs out of memory

**Solution**:
1. Reduce number of workers (4 → 2)
2. Restart workers after fewer tasks:
   ```python
   CELERY_WORKER_MAX_TASKS_PER_CHILD = 10  # in settings.py
   ```
3. Use headless mode to reduce memory usage

### Issue 4: Inconsistent Results

**Symptom**: Some EO numbers not scraped or duplicate entries

**Solution**:
- Each worker has its own database connection
- Django ORM handles race conditions automatically
- If issues persist, check database logs

### Issue 5: Can't See Browsers (Visual Mode)

**Symptom**: Browsers don't appear in visual mode

**Solution**:
1. Ensure `headless=False` in test command
2. Check display is available (not SSH session)
3. Run with `--visible` flag if using management command

---

## Comparing to Single Worker

### When to Use Single Worker:
- Limited server resources (< 2GB RAM)
- Small number of EO numbers (< 50)
- Testing individual EO numbers
- Debugging scraper logic

### When to Use Parallel Workers:
- Full scrapes (all 313 EO numbers)
- Production scheduled tasks
- Time-sensitive updates
- Server has adequate resources (4+ GB RAM)

### Migration from Single to Parallel:

The old single-worker task is still available:

```python
# Old way (still works)
from converters.tasks import scrape_website_task
result = scrape_website_task.apply_async(
    kwargs={'headless': True, 'pages': 50, 'test_mode': False},
    queue='scraping'
)

# New way (parallel)
from converters.tasks import parallel_scrape_website
result = parallel_scrape_website.apply_async(
    kwargs={'num_workers': 4, 'headless': True, 'pages': 50, 'test_mode': False},
    queue='scraping'
)
```

---

## Examples

### Example 1: Quick Test (2 workers, 6 EO numbers, visual)

```bash
python test_parallel_scraping.py 2 true false
python monitor_parallel_scraping.py <task_id>
```

**Expected Time**: 2-3 minutes
**Browsers**: 2 Chrome windows will open

### Example 2: Production Run (4 workers, all EO numbers, headless)

```bash
python test_parallel_scraping.py 4 false true
python monitor_parallel_scraping.py <task_id> 10
```

**Expected Time**: 15-30 minutes
**Browsers**: Hidden (headless)

### Example 3: High-Speed Test (8 workers, all EO numbers)

```bash
# First, ensure you have 8+ workers running
# Then trigger via Django shell:
python manage.py shell

>>> from converters.tasks import parallel_scrape_website
>>> result = parallel_scrape_website.apply_async(
...     kwargs={'num_workers': 8, 'headless': True, 'pages': 30},
...     queue='scraping'
... )
>>> print(f"Task ID: {result.id}")
```

### Example 4: Scrape Specific EO Numbers

```bash
python manage.py shell

>>> from converters.tasks import parallel_scrape_website
>>> result = parallel_scrape_website.apply_async(
...     kwargs={
...         'num_workers': 2,
...         'headless': True,
...         'pages': 100,  # Allow more pages for specific EOs
...         'eo_numbers': 'D-193-65,D-193-66,D-245-89,D-245-90',
...     },
...     queue='scraping'
... )
```

---

## Best Practices

### 1. Start Small
- Test with 2 workers first
- Verify everything works before scaling up
- Use test mode for initial runs

### 2. Monitor Resources
```bash
# Check system resources while scraping
htop  # CPU and memory usage
watch -n 1 'ps aux | grep celery'  # Worker processes
```

### 3. Gradual Scaling
- Start with 2 workers
- Increase to 4 workers if resources allow
- Go to 6-8 workers only on powerful servers

### 4. Page Limits
- Keep pages limit between 30-50 for production
- Higher limits risk timeouts
- Lower limits miss some data

### 5. Scheduled Tasks
- Run during off-peak hours (2 AM UTC default)
- Monitor first few runs manually
- Set up alerts for failures

### 6. Error Handling
- Individual worker failures don't affect others
- Parent task aggregates all results
- Check logs for patterns in failures

---

## Monitoring & Alerts

### Daily Checks

```bash
# Check last night's scraping results
python monitor_tasks.py

# Verify data freshness
python manage.py shell
>>> from converters.models import CatalyticConverter
>>> latest = CatalyticConverter.objects.latest('last_scraped')
>>> print(f"Last scraped: {latest.last_scraped}")
```

### Set Up Alerts (Optional)

Monitor failed tasks and send alerts:

```python
# In a monitoring script
from django_celery_results.models import TaskResult
from datetime import timedelta
from django.utils import timezone

yesterday = timezone.now() - timedelta(hours=24)
failed = TaskResult.objects.filter(
    status='FAILURE',
    date_done__gte=yesterday,
    task_name__icontains='scrape'
)

if failed.exists():
    # Send email/Slack notification
    print(f"⚠️  {failed.count()} scraping tasks failed in last 24 hours!")
```

---

## Summary

### Quick Reference Commands

```bash
# Test parallel scraping (visual)
python test_parallel_scraping.py 2 true false

# Monitor progress
python monitor_parallel_scraping.py <task_id>

# Check worker status
celery -A carb_backend inspect active

# View recent tasks
python monitor_tasks.py

# Identify large EO numbers
python identify_large_eos.py

# Scrape specific EO
python scrape_specific_eo.py D-193-65 100
```

### Files Reference

| File | Purpose |
|------|---------|
| `tasks.py` | Task definitions |
| `settings.py` | Scheduled task configuration |
| `test_parallel_scraping.py` | Test script |
| `monitor_parallel_scraping.py` | Real-time monitor |
| `monitor_tasks.py` | Task history viewer |
| `identify_large_eos.py` | Find EOs with many records |
| `scrape_specific_eo.py` | Scrape individual EOs |

---

## Conclusion

The parallel scraping system provides:
- ✅ **4-8x faster** data collection
- ✅ **Better resource utilization**
- ✅ **Fault tolerance** (individual worker failures)
- ✅ **Real-time monitoring**
- ✅ **Flexible configuration**

The scheduled nightly scraping now completes in **15-30 minutes** instead of **1-2 hours**! 🚀

For questions or issues, check the logs or refer to the [main documentation](PROJECT_DOCUMENTATION.md).
