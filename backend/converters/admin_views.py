"""
Admin views for data scraping operations
Allows staff users to trigger scraping from the Django admin interface
"""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.core.management import call_command
from django.http import JsonResponse, StreamingHttpResponse
from django.core.cache import cache
import io
import sys
import threading
import time
from .models import CatalyticConverter, Manufacturer
from .scraper import CARBScraper, CARBDataProcessor


@staff_member_required
def scraper_dashboard(request):
    """
    Main dashboard for scraping operations
    Shows stats and provides buttons to trigger scraping
    """
    context = {
        'title': 'Data Scraping Dashboard',
        'total_converters': CatalyticConverter.objects.count(),
        'total_manufacturers': Manufacturer.objects.count(),
        'active_converters': CatalyticConverter.objects.filter(is_active=True).count(),
        'last_scraped': CatalyticConverter.objects.filter(
            last_scraped__isnull=False
        ).order_by('-last_scraped').first(),
    }
    return render(request, 'admin/converters/scraper_dashboard.html', context)


@staff_member_required
def run_pdf_scraper(request):
    """
    Trigger PDF scraping operation
    """
    if request.method == 'POST':
        use_local = request.POST.get('use_local', 'true') == 'true'
        limit = request.POST.get('limit', None)

        try:
            # Capture command output
            out = io.StringIO()
            err = io.StringIO()

            # Prepare command arguments
            cmd_args = ['--source=pdf']
            if limit:
                cmd_args.append(f'--limit={limit}')
            if use_local:
                cmd_args.append('--use-local')
            else:
                cmd_args.append('--remote')

            # Run the scraping command
            call_command('scrape_carb_data', *cmd_args, stdout=out, stderr=err)

            # Get output
            output = out.getvalue()
            error = err.getvalue()

            if error:
                messages.warning(request, f'Scraping completed with warnings: {error}')
            else:
                messages.success(request, 'PDF scraping completed successfully!')

            # Add output to messages for display
            if output:
                for line in output.split('\n'):
                    if line.strip():
                        messages.info(request, line.strip())

        except Exception as e:
            messages.error(request, f'Error during PDF scraping: {str(e)}')

        return redirect('admin:scraper_dashboard')

    return redirect('admin:scraper_dashboard')


def run_scraper_background(scraper_type, cmd_name, cmd_args, task_id):
    """Helper function to run scraper in background thread"""
    import re
    import logging

    def strip_ansi_codes(text):
        """Remove ANSI color codes from text"""
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    try:
        cache.set(f'scraper_{task_id}_status', 'running', timeout=3600)
        cache.set(f'scraper_{task_id}_output', [], timeout=3600)

        # Capture output line by line
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
                        # Update cache immediately for each line
                        cache.set(f'scraper_{task_id}_output', output_lines.copy(), timeout=3600)

                # Also process buffer if it has content (for lines without \n)
                if buffer.strip() and not '\n' in buffer:
                    line = strip_ansi_codes(buffer).strip()
                    if line and len(output_lines) > 0 and output_lines[-1] != line:
                        output_lines.append(line)
                        cache.set(f'scraper_{task_id}_output', output_lines.copy(), timeout=3600)

            def flush(self):
                nonlocal buffer
                if buffer.strip():
                    line = strip_ansi_codes(buffer).strip()
                    if line:
                        output_lines.append(line)
                        cache.set(f'scraper_{task_id}_output', output_lines.copy(), timeout=3600)
                    buffer = ""

        # Custom logging handler to capture logger output
        class CacheLogHandler(logging.Handler):
            def emit(self, record):
                try:
                    msg = self.format(record)
                    msg = strip_ansi_codes(msg).strip()
                    if msg:
                        output_lines.append(msg)
                        cache.set(f'scraper_{task_id}_output', output_lines.copy(), timeout=3600)
                except Exception:
                    pass

        out = OutputCapture()

        # Setup logging capture
        log_handler = CacheLogHandler()
        log_handler.setLevel(logging.INFO)

        # Get the converters logger (used by eo_scraper)
        converters_logger = logging.getLogger('converters')
        original_level = converters_logger.level
        converters_logger.setLevel(logging.INFO)
        converters_logger.addHandler(log_handler)

        try:
            # Run the command
            call_command(cmd_name, *cmd_args, stdout=out, stderr=out)
        finally:
            # Remove our custom handler
            converters_logger.removeHandler(log_handler)
            converters_logger.setLevel(original_level)

        # Flush any remaining buffer
        out.flush()

        # Mark as completed
        cache.set(f'scraper_{task_id}_status', 'completed', timeout=3600)
        cache.set(f'scraper_{task_id}_output', output_lines, timeout=3600)

    except Exception as e:
        cache.set(f'scraper_{task_id}_status', 'error', timeout=3600)
        cache.set(f'scraper_{task_id}_error', str(e), timeout=3600)
        # Add error to output
        if 'output_lines' in locals():
            output_lines.append(f"ERROR: {str(e)}")
            cache.set(f'scraper_{task_id}_output', output_lines, timeout=3600)


@staff_member_required
def run_website_scraper(request):
    """
    Trigger website scraping operation using EO-based scraper
    """
    if request.method == 'POST':
        headless = request.POST.get('headless', 'true') == 'true'
        pages = request.POST.get('pages', '3')
        test_mode = request.POST.get('test_mode', 'false') == 'true'
        eo_numbers = request.POST.get('eo_numbers', '').strip()

        # Generate unique task ID
        task_id = f"website_{int(time.time())}"

        # Prepare command arguments for scrape_by_eo
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

        # Start scraper in background thread
        thread = threading.Thread(
            target=run_scraper_background,
            args=('website', 'scrape_by_eo', cmd_args, task_id)
        )
        thread.daemon = True
        thread.start()

        # Redirect to progress page
        return redirect(f'/admin/scraper-dashboard/progress/?task_id={task_id}&type=website')

    return redirect('admin:scraper_dashboard')


@staff_member_required
def run_combined_scraper(request):
    """
    Trigger both PDF and EO-based website scraping operations
    """
    if request.method == 'POST':
        try:
            # Capture command output
            out = io.StringIO()
            err = io.StringIO()

            # Step 1: Run PDF scraper
            messages.info(request, '📄 Starting PDF scraper...')
            call_command('scrape_carb_data', '--source=pdf', '--use-local',
                        stdout=out, stderr=err)

            pdf_output = out.getvalue()

            # Step 2: Run EO-based website scraper
            messages.info(request, '🌐 Starting EO-based website scraper...')
            out = io.StringIO()
            err = io.StringIO()

            call_command('scrape_by_eo', '--headless', '--pages=3',
                        stdout=out, stderr=err)

            web_output = out.getvalue()
            error = err.getvalue()

            if error:
                messages.warning(request, f'Scraping completed with some warnings')
            else:
                messages.success(request, '✓ Combined scraping completed successfully!')

            # Parse and display results from both scrapers
            messages.info(request, '=== PDF Scraper Results ===')
            for line in pdf_output.split('\n'):
                line = line.strip()
                if line and any(keyword in line for keyword in ['Found', 'Created', 'Updated', 'Total', 'Errors']):
                    messages.info(request, line)

            messages.info(request, '=== Website Scraper Results ===')
            for line in web_output.split('\n'):
                line = line.strip()
                if line and any(keyword in line for keyword in ['Total EOs', 'Successful', 'converters', 'Created', 'Updated']):
                    messages.info(request, line)

        except Exception as e:
            messages.error(request, f'Error during combined scraping: {str(e)}')

        return redirect('admin:scraper_dashboard')

    return redirect('admin:scraper_dashboard')


@staff_member_required
def scraper_stats_api(request):
    """
    JSON endpoint for dashboard stats
    """
    stats = {
        'total_converters': CatalyticConverter.objects.count(),
        'total_manufacturers': Manufacturer.objects.count(),
        'active_converters': CatalyticConverter.objects.filter(is_active=True).count(),
        'inactive_converters': CatalyticConverter.objects.filter(is_active=False).count(),
    }

    last_scraped = CatalyticConverter.objects.filter(
        last_scraped__isnull=False
    ).order_by('-last_scraped').first()

    if last_scraped:
        stats['last_scraped_date'] = last_scraped.last_scraped.isoformat()
    else:
        stats['last_scraped_date'] = None

    return JsonResponse(stats)


@staff_member_required
def scraper_progress_page(request):
    """
    Progress page that shows real-time scraping status
    """
    task_id = request.GET.get('task_id')
    scraper_type = request.GET.get('type', 'unknown')

    context = {
        'title': f'{scraper_type.title()} Scraper Progress',
        'task_id': task_id,
        'scraper_type': scraper_type,
    }
    return render(request, 'admin/converters/scraper_progress.html', context)


@staff_member_required
def scraper_progress_api(request):
    """
    API endpoint to get current scraping progress
    """
    task_id = request.GET.get('task_id')

    if not task_id:
        return JsonResponse({'error': 'No task_id provided'}, status=400)

    status = cache.get(f'scraper_{task_id}_status', 'unknown')
    output = cache.get(f'scraper_{task_id}_output', [])
    error = cache.get(f'scraper_{task_id}_error', None)

    return JsonResponse({
        'status': status,
        'output': output,
        'error': error,
    })
