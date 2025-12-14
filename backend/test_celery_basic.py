#!/usr/bin/env python3
"""
Test basic Celery functionality
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')
django.setup()

from carb_backend.celery import app

print("="*80)
print("TESTING BASIC CELERY FUNCTIONALITY")
print("="*80)
print()

# Test 1: Check configuration
print("Test 1: Checking Celery Configuration")
print(f"  Broker: {app.conf.broker_url}")
print(f"  Result Backend: {app.conf.result_backend}")
print(f"  Backend type: {type(app.backend)}")
print()

# Test 2: Simple task
print("Test 2: Testing simple task execution...")
result = app.send_task('carb_backend.celery.debug_task')
print(f"  Task ID: {result.id}")
print(f"  Task State: {result.state}")

# Wait for task
for i in range(10):
    time.sleep(1)
    state = result.state
    print(f"  [{i+1}s] State: {state}")

    if state != 'PENDING':
        print(f"  ✓ Task picked up by worker! State: {state}")
        if result.ready():
            print(f"  ✓ Task completed!")
            print(f"  Result: {result.result}")
        break
else:
    print("  ✗ Task stuck in PENDING - workers not picking up tasks")

print()
print("="*80)
