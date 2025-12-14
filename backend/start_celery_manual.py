#!/usr/bin/env python3
"""
Manually start Celery worker to ensure settings are loaded correctly
"""
import os
import sys

# Setup Django FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')

import django
django.setup()

# Now import Celery
from carb_backend.celery import app

# Print configuration to verify
print("="*80)
print("CELERY CONFIGURATION CHECK")
print("="*80)
print(f"Broker URL: {app.conf.broker_url}")
print(f"Result Backend: {app.conf.result_backend}")
print(f"Result Extended: {app.conf.result_extended}")
print(f"Result Expires: {app.conf.result_expires}")
print("="*80)
print()

if not app.conf.result_backend:
    print("⚠️  WARNING: Result backend is not configured!")
    print("Setting it now...")
    app.conf.result_backend = 'redis://localhost:6379/1'
    print(f"✓ Result backend set to: {app.conf.result_backend}")
    print()

# Start the worker
print("Starting Celery worker...")
worker = app.Worker(
    loglevel='INFO',
    pool='solo',
)
worker.start()
