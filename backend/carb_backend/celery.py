"""
Celery configuration for CARB Backend
"""
import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
import logging

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'carb_backend.settings')

# Create Celery app with explicit broker and result backend
app = Celery(
    'carb_backend',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1'  # Set result backend at initialization
)

# Load configuration from Django settings with CELERY_ namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Override with explicit settings (ensure they stick)
app.conf.update(
    result_backend='redis://localhost:6379/1',
    result_extended=True,
    result_expires=3600 * 24,
    result_serializer='json',
    accept_content=['json'],
    task_serializer='json',
    task_track_started=True,
    task_send_sent_event=True,
)

# Allow coordinator tasks to wait for subtask results (needed for parallel scraping)
app.conf.task_allow_error_cb_on_chord_header = True

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """Log when a task starts"""
    logger.info(f"Task {task.name} [{task_id}] started")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """Log when a task completes"""
    logger.info(f"Task {task.name} [{task_id}] completed with state: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """Log when a task fails"""
    logger.error(f"Task {sender.name} [{task_id}] failed: {exception}")


@app.task(bind=True)
def debug_task(self):
    """Debug task to test Celery is working"""
    print(f'Request: {self.request!r}')
