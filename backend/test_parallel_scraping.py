#!/usr/bin/env python3
"""
Test parallel scraping with the new group-based implementation
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from converters.tasks import parallel_scrape_website
import time

print("="*80)
print("TESTING PARALLEL SCRAPING WITH PLAYWRIGHT")
print("="*80)
print()

# Launch parallel scraping with 4 workers in test mode
print("Launching parallel scraping task...")
print("  - Workers: 4")
print("  - Test Mode: True (first 12 EOs only)")
print("  - Pages per EO: 50")
print()

result = parallel_scrape_website.delay(
    num_workers=4,
    headless=True,
    pages=50,
    test_mode=True  # Only scrapes first 12 EOs
)

print(f"✓ Task launched successfully!")
print(f"  Task ID: {result.id}")
print()

print("Monitoring task progress...")
print("-"*80)

# Monitor progress
for i in range(60):  # Check for up to 60 seconds
    time.sleep(2)

    state = result.state

    if state == 'PENDING':
        print(f"[{i*2}s] Status: PENDING - Waiting for worker to pick up task...")
    elif state == 'PROGRESS':
        info = result.info
        status = info.get('status', 'Unknown')
        current = info.get('current', 0)
        total = info.get('total', 100)
        progress_pct = (current / total * 100) if total > 0 else 0
        print(f"[{i*2}s] Status: PROGRESS ({progress_pct:.0f}%) - {status}")

        # Show worker details if available
        if 'completed_workers' in info:
            print(f"       Workers: {info['completed_workers']}/{info['total_workers']} completed, {info.get('failed_workers', 0)} failed")
    elif state == 'SUCCESS':
        print(f"[{i*2}s] Status: SUCCESS - Task completed!")
        print()
        print("Final Results:")
        print("-"*80)
        result_data = result.result
        print(f"  Status: {result_data.get('status')}")
        print(f"  Workers: {result_data.get('num_workers')}")
        print(f"  Completed: {result_data.get('completed_workers')}")
        print(f"  Failed: {result_data.get('failed_workers')}")
        print()
        stats = result_data.get('stats', {})
        print(f"  Success Count: {stats.get('success_count')}")
        print(f"  Failed Count: {stats.get('failed_count')}")
        print(f"  No Results: {stats.get('no_results_count')}")
        print(f"  Converters Created: {stats.get('converters_created')}")
        print(f"  Converters Updated: {stats.get('converters_updated')}")
        break
    elif state == 'FAILURE':
        print(f"[{i*2}s] Status: FAILURE - Task failed!")
        print(f"Error: {result.traceback}")
        break
    else:
        print(f"[{i*2}s] Status: {state}")

    if result.ready():
        break

print()
print("="*80)
print("View detailed results in Django Admin:")
print("http://localhost:8000/admin/converters/scraperrun/")
print("="*80)
