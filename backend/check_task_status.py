#!/usr/bin/env python3
"""
Check status of a specific Celery task
Usage: python check_task_status.py <task_id>
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from celery.result import AsyncResult
from carb_backend.celery import app

if len(sys.argv) > 1:
    task_id = sys.argv[1]
else:
    task_id = '18dfb5d7-d35c-4fd1-ab20-8b5633a89934'  # Your stuck task

print(f"Checking task: {task_id}")
print("="*80)

result = AsyncResult(task_id, app=app)

print(f"State: {result.state}")
print(f"Ready: {result.ready()}")
print(f"Successful: {result.successful()}")
print(f"Failed: {result.failed()}")

if result.state == 'PROGRESS':
    print(f"\nProgress Info:")
    print(result.info)
elif result.state == 'FAILURE':
    print(f"\nError: {result.traceback}")
elif result.ready():
    print(f"\nResult: {result.result}")
else:
    print(f"\nInfo: {result.info}")

# Check if task is in queue
from django.core.cache import cache
cache_key = f'parallel_scrape_{task_id}'
cache_data = cache.get(cache_key)

if cache_data:
    print(f"\nCache data found:")
    print(f"  - Parent Task ID: {cache_data.get('parent_task_id')}")
    print(f"  - Group ID: {cache_data.get('group_id')}")
    print(f"  - Num Workers: {cache_data.get('num_workers')}")
    print(f"  - Total EOs: {cache_data.get('total_eos')}")
    print(f"  - Worker Task IDs: {cache_data.get('worker_task_ids')}")
else:
    print(f"\nNo cache data found for key: {cache_key}")
