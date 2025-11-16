"""
Celery tasks for CARB data scraping operations
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from django.core.cache import cache
import io
import sys
import re

logger = get_task_logger(__name__)


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


@shared_task(bind=True, name='converters.tasks.scrape_website_task')
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

                        # Update progress based on output
                        if 'Processing EO:' in line or 'Processing page' in line:
                            # Extract progress if possible
                            self.update_state(
                                state='PROGRESS',
                                meta={
                                    'status': line,
                                    'current': len(output_lines),
                                    'total': 100,
                                    'output': output_lines[-50:],  # Keep last 50 lines
                                }
                            )

            def flush(self):
                nonlocal buffer
                if buffer.strip():
                    line = strip_ansi_codes(buffer).strip()
                    if line:
                        output_lines.append(line)
                        logger.info(line)
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
        call_command('scrape_by_eo', *cmd_args, stdout=out, stderr=out)
        out.flush()

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
