"""
Celery tasks for CARB data scraping operations
"""
from celery import shared_task, group
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.core.cache import cache
import io
import sys
import re
import logging
import math

logger = get_task_logger(__name__)

SCRAPER_LOG_PREFIXES = {
    'pdf': [
        'converters.scraper',
        'converters.management.commands.scrape_carb_data',
    ],
    'website': [
        'converters.eo_scraper',
        'converters.management.commands.scrape_by_eo',
    ],
}


class ScraperProgressHandler(logging.Handler):
    """
    Stream scraper logs into Celery progress updates so the Django admin can show
    live output while a task is running.
    """

    def __init__(self, task_ref, output_lines, allowed_prefixes):
        super().__init__()
        self.task_ref = task_ref
        self.output_lines = output_lines
        self.allowed_prefixes = allowed_prefixes or []

    def emit(self, record):
        name = record.name or ''
        if self.allowed_prefixes and not any(
            name == prefix or name.startswith(prefix + '.')
            for prefix in self.allowed_prefixes
        ):
            return

        try:
            message = self.format(record)
        except Exception:
            return

        message = strip_ansi_codes(message).rstrip()
        if not message:
            return

        self.output_lines.append(message)
        try:
            self.task_ref.update_state(
                state='PROGRESS',
                meta={
                    'status': message,
                    'current': len(self.output_lines),
                    'total': 100,
                    'output': self.output_lines[:],
                }
            )
        except Exception as exc:
            # Avoid crashing the worker if the backend temporarily rejects updates
            logger.warning("Failed to push scraper progress update: %s", exc, exc_info=True)


def attach_progress_handler(task_ref, output_lines, *, allowed_prefixes):
    """
    Attach the scraper progress handler and return (root_logger, handler) so it
    can be removed after the management command finishes.
    """
    handler = ScraperProgressHandler(task_ref, output_lines, allowed_prefixes)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter('%(message)s'))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    for prefix in allowed_prefixes:
        logging.getLogger(prefix).setLevel(logging.INFO)

    return root_logger, handler


def strip_ansi_codes(text):
    """Remove ANSI color codes from text"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


@shared_task(bind=True, name='converters.tasks.scrape_pdf_task')
def scrape_pdf_task(self, use_local=True, limit=None):
    """
    Celery task to scrape PDF data

    Args:
        use_local (bool): Whether to use local PDF file
        limit (int): Limit number of records to scrape (optional)

    Returns:
        dict: Scraping statistics
    """
    logger.info(f"Starting PDF scraping task {self.request.id}")

    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Initializing PDF scraper...',
                'current': 0,
                'total': 100,
            }
        )

        # Capture command output
        output_lines = []
        buffer = ""
        task_ref = self

        class OutputCapture:
            def write(self, text):
                nonlocal buffer
                buffer += text

                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = strip_ansi_codes(line).strip()
                    if line:
                        output_lines.append(line)
                        logger.info(line)

            def flush(self):
                nonlocal buffer
                if buffer.strip():
                    line = strip_ansi_codes(buffer).strip()
                    if line:
                        output_lines.append(line)
                        logger.info(line)
                    buffer = ""

        out = OutputCapture()

        root_logger = progress_handler = None
        try:
            root_logger, progress_handler = attach_progress_handler(
                task_ref,
                output_lines,
                allowed_prefixes=SCRAPER_LOG_PREFIXES['pdf'],
            )

            # Prepare command arguments
            cmd_args = ['--source=pdf']
            if limit:
                cmd_args.append(f'--limit={limit}')
            if use_local:
                cmd_args.append('--use-local')
            else:
                cmd_args.append('--remote')

            # Update progress
            self.update_state(
                state='PROGRESS',
                meta={
                    'status': 'Running PDF scraper...',
                    'current': 10,
                    'total': 100,
                    'output': output_lines,
                }
            )

            # Run the scraping command
            call_command('scrape_carb_data', *cmd_args, stdout=out, stderr=out)
            out.flush()

            # Mark as completed
            logger.info(f"PDF scraping task {self.request.id} completed successfully")

            return {
                'status': 'completed',
                'output': output_lines,
                'message': 'PDF scraping completed successfully',
            }
        finally:
            if root_logger and progress_handler:
                root_logger.removeHandler(progress_handler)

    except Exception as e:
        logger.error(f"PDF scraping task {self.request.id} failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Error during PDF scraping',
                'error': str(e),
                'output': output_lines if 'output_lines' in locals() else [],
            }
        )
        raise


@shared_task(
    bind=True,
    name='converters.tasks.scrape_website_task',
    soft_time_limit=20 * 60 * 60,  # Allow 20 hours before soft timeout for large runs
    time_limit=(20 * 60 * 60) + 300,  # Hard limit trails soft limit by 5 minutes
)
def scrape_website_task(self, headless=True, pages=None, test_mode=False, eo_numbers=None):
    """
    Celery task to scrape website data using EO-based scraper

    Args:
        headless (bool): Run browser in headless mode
        pages (int): Maximum pages to scrape per EO (None for unlimited)
        test_mode (bool): Test mode (scrape only first 3 EO numbers)
        eo_numbers (str): Comma-separated list of specific EO numbers

    Returns:
        dict: Scraping statistics
    """
    logger.info(f"Starting website scraping task {self.request.id}")

    try:
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Initializing website scraper...',
                'current': 0,
                'total': 100,
            }
        )

        # Capture command output
        output_lines = []
        buffer = ""

        task_ref = self  # capture Celery task reference for nested writer

        class OutputCapture:
            def write(self, text):
                nonlocal buffer
                buffer += text

                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = strip_ansi_codes(line).strip()
                    if line:
                        output_lines.append(line)
                        logger.info(line)

                        # Push the most recent lines to the progress API so the admin UI
                        # shows streaming logs instead of waiting for task completion.
                        task_ref.update_state(
                            state='PROGRESS',
                            meta={
                                'status': line,
                                'current': len(output_lines),
                                'total': 100,
                                'output': output_lines[:],  # Send full log history
                            }
                        )

            def flush(self):
                nonlocal buffer
                if buffer.strip():
                    line = strip_ansi_codes(buffer).strip()
                    if line:
                        output_lines.append(line)
                        logger.info(line)
                        task_ref.update_state(
                            state='PROGRESS',
                            meta={
                                'status': line,
                                'current': len(output_lines),
                                'total': 100,
                                'output': output_lines[:],
                            }
                        )
                    buffer = ""

        out = OutputCapture()

        # Prepare command arguments
        cmd_args = []
        if headless:
            cmd_args.append('--headless')
        else:
            cmd_args.append('--visible')

        if pages:
            cmd_args.append(f'--pages={pages}')

        if test_mode:
            cmd_args.append('--test')

        if eo_numbers:
            cmd_args.append(f'--eo-numbers={eo_numbers}')

        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={
                'status': 'Running website scraper...',
                'current': 10,
                'total': 100,
                'output': output_lines,
            }
        )

        # Run the scraping command
        try:
            root_logger, progress_handler = attach_progress_handler(
                task_ref,
                output_lines,
                allowed_prefixes=SCRAPER_LOG_PREFIXES['website'],
            )
            call_command('scrape_by_eo', *cmd_args, stdout=out, stderr=out)
            out.flush()
        finally:
            if root_logger and progress_handler:
                root_logger.removeHandler(progress_handler)

        # Parse statistics from output
        stats = {
            'total_eos': 0,
            'successful_eos': 0,
            'failed_eos': 0,
            'total_converters': 0,
            'created': 0,
            'updated': 0,
        }

        for line in output_lines:
            if 'Total EOs processed:' in line:
                stats['total_eos'] = int(line.split(':')[-1].strip())
            elif 'Successful:' in line:
                stats['successful_eos'] = int(line.split(':')[-1].strip())
            elif 'Failed:' in line:
                stats['failed_eos'] = int(line.split(':')[-1].strip())
            elif 'Total converters found:' in line:
                stats['total_converters'] = int(line.split(':')[-1].strip())
            elif 'Created:' in line:
                stats['created'] = int(line.split(':')[-1].split()[0].strip())
            elif 'Updated:' in line:
                stats['updated'] = int(line.split(':')[-1].split()[0].strip())

        # Mark as completed
        logger.info(f"Website scraping task {self.request.id} completed successfully")

        return {
            'status': 'completed',
            'output': output_lines,
            'stats': stats,
            'message': 'Website scraping completed successfully',
        }

    except Exception as e:
        logger.error(f"Website scraping task {self.request.id} failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={
                'status': 'Error during website scraping',
                'error': str(e),
                'output': output_lines if 'output_lines' in locals() else [],
            }
        )
        raise


@shared_task(name='converters.tasks.cleanup_old_task_results')
def cleanup_old_task_results():
    """
    Periodic task to cleanup old task results from database
    Runs daily to keep the database clean
    """
    from django_celery_results.models import TaskResult
    from django.utils import timezone
    from datetime import timedelta

    logger.info("Starting cleanup of old task results")

    # Delete task results older than 7 days
    cutoff_date = timezone.now() - timedelta(days=7)
    deleted_count, _ = TaskResult.objects.filter(date_done__lt=cutoff_date).delete()

    logger.info(f"Cleaned up {deleted_count} old task results")

    return {
        'deleted_count': deleted_count,
        'cutoff_date': cutoff_date.isoformat(),
    }


# ============================================================================
# PARALLEL SCRAPING TASKS
# ============================================================================

@shared_task(
    bind=True,
    name='converters.tasks.scrape_eo_batch',
    soft_time_limit=20 * 60 * 60,  # 20 hours per batch
    time_limit=(20 * 60 * 60) + 300,
)
def scrape_eo_batch(self, eo_batch, batch_number, total_batches, headless=True, pages=50):
    """
    Scrape a specific batch of EO numbers

    Args:
        eo_batch (list): List of EO numbers to scrape
        batch_number (int): Current batch number (for progress tracking)
        total_batches (int): Total number of batches
        headless (bool): Run browser in headless mode
        pages (int): Maximum pages to scrape per EO

    Returns:
        dict: Scraping statistics for this batch
    """
    from converters.eo_scraper import CARBEOScraper

    logger.info(f"Starting batch {batch_number}/{total_batches} with {len(eo_batch)} EO numbers")

    # Store logs for this worker
    worker_logs = []
    worker_logs.append(f"🚀 Worker {batch_number} started")
    worker_logs.append(f"📋 Processing {len(eo_batch)} EO numbers")
    worker_logs.append(f"🌐 Headless mode: {headless}, Max pages: {pages}")

    # Update task state with initial progress
    self.update_state(
        state='PROGRESS',
        meta={
            'batch_number': batch_number,
            'total_batches': total_batches,
            'eo_count': len(eo_batch),
            'current': 0,
            'total': len(eo_batch),
            'status': f'Starting batch {batch_number}/{total_batches}...',
            'logs': worker_logs,
        }
    )

    scraper = None
    try:
        worker_logs.append(f"🔧 Initializing web scraper...")
        scraper = CARBEOScraper(headless=headless, pages_per_eo=pages)
        worker_logs.append(f"✅ Scraper initialized successfully")

        # Update progress before scraping
        self.update_state(
            state='PROGRESS',
            meta={
                'batch_number': batch_number,
                'total_batches': total_batches,
                'eo_count': len(eo_batch),
                'current': 0,
                'total': len(eo_batch),
                'status': f'Scraping {len(eo_batch)} EOs...',
                'logs': worker_logs,
            }
        )

        # Scrape this batch of EO numbers with detailed logging
        worker_logs.append(f"🔍 Starting to scrape EO numbers...")
        worker_logs.append(f"=" * 60)

        # Set up a custom log handler that captures logs in real-time
        import logging

        class WorkerLogHandler(logging.Handler):
            def __init__(self, log_list, task_obj, batch_number, total_batches, eo_count):
                super().__init__()
                self.log_list = log_list
                self.task_obj = task_obj
                self.batch_number = batch_number
                self.total_batches = total_batches
                self.eo_count = eo_count
                self.update_counter = 0

            def emit(self, record):
                try:
                    msg = self.format(record)
                    self.log_list.append(msg)

                    # Update task state every 5 log messages for real-time progress
                    self.update_counter += 1
                    if self.update_counter >= 5:
                        self.update_counter = 0
                        self.task_obj.update_state(
                            state='PROGRESS',
                            meta={
                                'batch_number': self.batch_number,
                                'total_batches': self.total_batches,
                                'eo_count': self.eo_count,
                                'current': 0,
                                'total': self.eo_count,
                                'status': f'Scraping batch {self.batch_number}...',
                                'logs': self.log_list[-50:],  # Keep last 50 lines
                            }
                        )
                except Exception:
                    pass  # Don't let logging errors break the scraping

        # Add the custom handler
        scraper_logger = logging.getLogger('converters.eo_scraper')
        worker_log_handler = WorkerLogHandler(worker_logs, self, batch_number, total_batches, len(eo_batch))
        worker_log_handler.setLevel(logging.INFO)
        worker_log_handler.setFormatter(logging.Formatter('%(message)s'))

        original_level = scraper_logger.level
        scraper_logger.addHandler(worker_log_handler)
        scraper_logger.setLevel(logging.INFO)

        try:
            stats = scraper.scrape_by_eo_numbers(eo_batch)
        finally:
            # Remove the handler
            scraper_logger.removeHandler(worker_log_handler)
            scraper_logger.setLevel(original_level)

        worker_logs.append(f"=" * 60)
        worker_logs.append(f"✅ Scraping complete!")
        worker_logs.append(f"📊 Results: {stats.get('total_converters', 0)} converters found")
        worker_logs.append(f"   Created: {stats.get('created', 0)}, Updated: {stats.get('updated', 0)}")

        # Update final state
        self.update_state(
            state='PROGRESS',
            meta={
                'batch_number': batch_number,
                'total_batches': total_batches,
                'eo_count': len(eo_batch),
                'current': len(eo_batch),
                'total': len(eo_batch),
                'status': f'Batch {batch_number}/{total_batches} complete',
                'stats': stats,
                'logs': worker_logs[-50:],  # Keep last 50 log lines for detailed logs
            }
        )

        logger.info(f"Batch {batch_number} complete: {stats}")

        return {
            'batch_number': batch_number,
            'total_batches': total_batches,
            'eo_numbers': eo_batch,
            'stats': stats,
            'logs': worker_logs,
        }

    except Exception as e:
        logger.error(f"Batch {batch_number} failed: {e}")
        worker_logs.append(f"=" * 60)
        worker_logs.append(f"❌ Error: {str(e)}")
        self.update_state(
            state='PROGRESS',
            meta={
                'batch_number': batch_number,
                'total_batches': total_batches,
                'eo_count': len(eo_batch),
                'current': 0,
                'total': len(eo_batch),
                'status': f'Batch {batch_number} failed',
                'error': str(e),
                'logs': worker_logs[-50:],  # Keep last 50 log lines for detailed logs
            }
        )
        raise
    finally:
        if scraper:
            scraper._close_driver()


@shared_task(
    bind=True,
    name='converters.tasks.aggregate_parallel_results',
)
def aggregate_parallel_results(self, batch_results):
    """
    Callback task to aggregate results from parallel scraping batches

    Args:
        batch_results (list): List of results from each batch worker

    Returns:
        dict: Aggregated statistics from all workers
    """
    logger.info(f"Aggregating results from {len(batch_results)} batches")

    total_stats = {
        'total_eos': 0,
        'successful_eos': 0,
        'failed_eos': 0,
        'total_converters': 0,
        'created': 0,
        'updated': 0,
    }

    batch_details = []

    for batch_result in batch_results:
        if not batch_result:
            continue

        batch_stats = batch_result.get('stats', {})
        batch_details.append({
            'batch_number': batch_result.get('batch_number'),
            'eo_count': len(batch_result.get('eo_numbers', [])),
            'stats': batch_stats,
            'logs': batch_result.get('logs', []),  # Include worker logs
        })

        # Aggregate statistics
        for key in total_stats:
            if key in batch_stats:
                total_stats[key] += batch_stats[key]

    logger.info(f"Parallel scraping complete. Total stats: {total_stats}")

    return {
        'status': 'completed',
        'num_workers': len(batch_results),
        'stats': total_stats,
        'batch_details': batch_details,
    }


@shared_task(
    bind=True,
    name='converters.tasks.parallel_scrape_website',
    soft_time_limit=20 * 60 * 60,  # 20 hours total
    time_limit=(20 * 60 * 60) + 300,
)
def parallel_scrape_website(self, num_workers=4, headless=True, pages=50, test_mode=False, eo_numbers=None):
    """
    Coordinate parallel scraping across multiple workers using Celery chord

    Args:
        num_workers (int): Number of parallel workers (default: 4)
        headless (bool): Run browser in headless mode
        pages (int): Maximum pages to scrape per EO
        test_mode (bool): Test mode (scrape only first 12 EO numbers)
        eo_numbers (str): Comma-separated list of specific EO numbers

    Returns:
        dict: Aggregated scraping statistics from all workers
    """
    from celery import chord
    from converters.eo_scraper import CARBEOScraper
    import math

    logger.info(f"Starting parallel scraping with {num_workers} workers")

    # Update initial state
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 5,
            'total': 100,
            'status': 'Extracting EO numbers from website...',
            'num_workers': num_workers,
        }
    )

    # Step 1: Extract all EO numbers
    scraper = None
    try:
        scraper = CARBEOScraper(headless=True)

        if eo_numbers and eo_numbers.strip():
            # Use provided EO numbers
            all_eo_numbers = [eo.strip() for eo in eo_numbers.split(',') if eo.strip()]
            logger.info(f"Using {len(all_eo_numbers)} provided EO numbers")
        else:
            # Extract EO numbers from website
            logger.info("Extracting EO numbers from CARB website...")
            try:
                # IMPORTANT: Initialize the WebDriver before extracting EO numbers
                scraper._setup_driver()
                all_eo_numbers = scraper.extract_eo_numbers()
                logger.info(f"Successfully extracted {len(all_eo_numbers)} EO numbers from website")
            except Exception as extract_error:
                logger.error(f"Failed to extract EO numbers: {extract_error}")
                raise ValueError(f"Failed to extract EO numbers from CARB website: {str(extract_error)}")

        scraper._close_driver()
        scraper = None

        # Validate we have EO numbers
        if not all_eo_numbers or len(all_eo_numbers) == 0:
            error_msg = "No EO numbers available to scrape. The extraction from CARB website returned no results."
            logger.error(error_msg)
            raise ValueError(error_msg)

        if test_mode:
            # In test mode, use first 12 EO numbers (3 per worker with 4 workers)
            all_eo_numbers = all_eo_numbers[:12]
            logger.info(f"Test mode: Limited to {len(all_eo_numbers)} EO numbers")

        # Update state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 10,
                'total': 100,
                'status': f'Dividing {len(all_eo_numbers)} EO numbers across {num_workers} workers...',
                'num_workers': num_workers,
                'total_eos': len(all_eo_numbers),
            }
        )

        # Step 2: Divide EO numbers into batches
        # Ensure batch_size is at least 1
        batch_size = max(1, math.ceil(len(all_eo_numbers) / num_workers))
        batches = [
            all_eo_numbers[i:i + batch_size]
            for i in range(0, len(all_eo_numbers), batch_size)
        ]

        logger.info(f"Created {len(batches)} batches, ~{batch_size} EOs per batch")

        # Update state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 15,
                'total': 100,
                'status': f'Launching {len(batches)} parallel workers...',
                'num_workers': num_workers,
                'total_eos': len(all_eo_numbers),
                'batches': len(batches),
            }
        )

        # Step 3: Launch parallel tasks using chord (Celery's recommended approach)
        # A chord runs tasks in parallel and executes a callback when all complete
        import uuid

        # Create individual task signatures with explicit task IDs
        worker_tasks = []
        worker_task_ids = []
        worker_info = []

        for i, batch in enumerate(batches):
            # Generate a unique task ID for this worker
            task_id = str(uuid.uuid4())

            # Create the task signature with explicit ID
            task_signature = scrape_eo_batch.si(
                eo_batch=batch,
                batch_number=i + 1,
                total_batches=len(batches),
                headless=headless,
                pages=pages
            )
            # Set the task ID on the signature's options
            task_signature.set(task_id=task_id)

            worker_tasks.append(task_signature)
            worker_task_ids.append(task_id)
            worker_info.append({
                'batch_number': i + 1,
                'eo_numbers': batch,
                'eo_count': len(batch),
                'task_id': task_id,
            })

        logger.info(f"Generated worker task IDs: {worker_task_ids}")

        # Create the chord with callback
        callback = aggregate_parallel_results.s()
        chord_task = chord(worker_tasks)(callback)

        # The chord callback task ID
        chord_id = chord_task.id

        logger.info(f"Chord created - Callback ID: {chord_id}, Worker count: {len(worker_task_ids)}")

        # Update state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 20,
                'total': 100,
                'status': f'{len(batches)} workers launched, scraping in progress...',
                'num_workers': num_workers,
                'total_eos': len(all_eo_numbers),
                'batches': len(batches),
                'chord_id': chord_id,
                'worker_task_ids': worker_task_ids,
            }
        )

        # Store task info in cache for monitoring
        cache_key = f'parallel_scrape_{self.request.id}'
        cache_data = {
            'parent_task_id': self.request.id,
            'chord_id': chord_id,
            'num_workers': len(batches),
            'total_eos': len(all_eo_numbers),
            'worker_task_ids': worker_task_ids,
            'worker_info': worker_info,
        }
        cache.set(cache_key, cache_data, timeout=3600 * 6)  # 6 hours

        logger.info(f"Parallel scraping launched with {len(batches)} workers. Chord callback ID: {chord_id}, Worker IDs: {len(worker_task_ids)} captured")
        logger.info(f"Cache stored at key: {cache_key} with {len(worker_task_ids)} worker IDs")

        # Return the chord result ID so progress can be monitored
        return {
            'status': 'processing',
            'message': f'Parallel scraping started with {len(batches)} workers',
            'num_workers': len(batches),
            'total_eos': len(all_eo_numbers),
            'chord_id': chord_id,
        }

    except Exception as e:
        logger.error(f"Parallel scraping failed: {e}")
        if scraper:
            scraper._close_driver()
        raise
