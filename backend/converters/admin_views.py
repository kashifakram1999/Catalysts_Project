"""
Admin views for data scraping operations
Allows staff users to trigger scraping from the Django admin interface
"""

from datetime import datetime
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from celery.result import AsyncResult
from .models import CatalyticConverter, Manufacturer
from .tasks import scrape_pdf_task, scrape_website_task, parallel_scrape_website


def parse_scheduled_datetime(raw_value):
    """
    Convert the datetime-local form value into an aware datetime in the current timezone.
    """
    if not raw_value:
        return None

    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError('Invalid schedule date/time. Please use the picker above.') from exc

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


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
    Trigger PDF scraping operation using Celery
    """
    if request.method == 'POST':
        use_local = request.POST.get('use_local') == 'true'
        limit = request.POST.get('limit', None)
        scheduled_time_raw = request.POST.get('scheduled_time', '').strip()

        try:
            # Convert limit to int if provided
            limit_int = int(limit) if limit and limit.strip() else None

            # Parse scheduled datetime (optional)
            try:
                scheduled_time = parse_scheduled_datetime(scheduled_time_raw)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('admin:scraper_dashboard')

            task_kwargs = {
                'use_local': use_local,
                'limit': limit_int,
            }

            # Launch Celery task
            if scheduled_time and scheduled_time > timezone.now():
                eta = scheduled_time.astimezone(timezone.utc)
                task = scrape_pdf_task.apply_async(kwargs=task_kwargs, eta=eta)
                progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=pdf"
                display_time = timezone.localtime(scheduled_time).strftime('%B %d, %Y %I:%M %p %Z')
                messages.success(
                    request,
                    f'PDF scraping scheduled for {display_time}. Task ID: {task.id}. '
                    f'You can monitor it at {progress_url}'
                )
                return redirect('admin:scraper_dashboard')
            else:
                task = scrape_pdf_task.delay(**task_kwargs)
                progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=pdf"
                note = ''
                if scheduled_time:
                    note = ' (requested schedule was in the past, so it started immediately)'
                messages.success(
                    request,
                    f'PDF scraping task started! Task ID: {task.id}{note}'
                )

                # Redirect to progress page for live monitoring
                return redirect(progress_url)

        except Exception as e:
            messages.error(request, f'Error starting PDF scraping task: {str(e)}')

        return redirect('admin:scraper_dashboard')

    return redirect('admin:scraper_dashboard')


@staff_member_required
def run_website_scraper(request):
    """
    Trigger website scraping operation using Celery and EO-based scraper
    """
    if request.method == 'POST':
        headless = request.POST.get('headless') == 'true'
        pages = request.POST.get('pages', '').strip()  # Empty by default (scrape all pages)
        test_mode = request.POST.get('test_mode', 'false') == 'true'
        eo_numbers = request.POST.get('eo_numbers', '').strip()
        scheduled_time_raw = request.POST.get('scheduled_time', '').strip()

        try:
            # Convert pages to int if provided
            pages_int = int(pages) if pages else None

            # Parse scheduled datetime (optional)
            try:
                scheduled_time = parse_scheduled_datetime(scheduled_time_raw)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('admin:scraper_dashboard')

            task_kwargs = {
                'headless': headless,
                'pages': pages_int,
                'test_mode': test_mode,
                'eo_numbers': eo_numbers if eo_numbers else None,
            }

            # Launch Celery task
            if scheduled_time and scheduled_time > timezone.now():
                eta = scheduled_time.astimezone(timezone.utc)
                task = scrape_website_task.apply_async(kwargs=task_kwargs, eta=eta)
                progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=website"
                display_time = timezone.localtime(scheduled_time).strftime('%B %d, %Y %I:%M %p %Z')
                messages.success(
                    request,
                    f'Website scraping scheduled for {display_time}. Task ID: {task.id}. '
                    f'You can monitor it at {progress_url}'
                )
                return redirect('admin:scraper_dashboard')
            else:
                task = scrape_website_task.delay(**task_kwargs)
                progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=website"
                note = ''
                if scheduled_time:
                    note = ' (requested schedule was in the past, so it started immediately)'
                messages.success(
                    request,
                    f'Website scraping task started! Task ID: {task.id}{note}'
                )

                # Redirect to progress page
                return redirect(progress_url)

        except Exception as e:
            messages.error(request, f'Error starting website scraping task: {str(e)}')

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
    API endpoint to get current scraping progress from Celery task
    """
    task_id = request.GET.get('task_id')
    scraper_type = request.GET.get('type', 'unknown')

    if not task_id:
        return JsonResponse({'error': 'No task_id provided'}, status=400)

    try:
        # Check if this is a parallel scraping task
        if scraper_type == 'parallel':
            from django.core.cache import cache
            import logging
            logger = logging.getLogger(__name__)

            # Get worker task IDs from cache
            cache_key = f'parallel_scrape_{task_id}'
            cached_data = cache.get(cache_key)

            logger.info(f"Progress API called for parallel task {task_id}, cache_key: {cache_key}, cached_data found: {cached_data is not None}")

            if not cached_data:
                # Cache might not be populated yet, return pending status
                logger.warning(f"No cache data found for key: {cache_key}")
                return JsonResponse({
                    'status': 'pending',
                    'output': [
                        'Initializing parallel scraping...',
                        'Please wait while workers are being launched.',
                        f'(Looking for cache key: {cache_key})'
                    ],
                    'error': None,
                })

            if cached_data and 'chord_id' in cached_data:
                chord_id = cached_data['chord_id']
                worker_task_ids = cached_data.get('worker_task_ids', [])
                worker_info = cached_data.get('worker_info', [])

                # Check if worker task IDs are available
                if not worker_task_ids:
                    return JsonResponse({
                        'status': 'running',
                        'output': [
                            '⚡ Parallel scraping is starting...',
                            '',
                            f"Workers are being launched. Please wait...",
                            f"Total EOs: {cached_data.get('total_eos', 'Unknown')}",
                        ],
                        'error': None,
                    })

                # Get the chord callback task
                chord_result = AsyncResult(chord_id)

                # Check chord state
                if chord_result.state == 'SUCCESS':
                    # All workers completed
                    result = chord_result.result
                    batch_details = result.get('batch_details', [])

                    # Build output with worker summaries
                    output = [
                        '✅ All workers completed successfully!',
                        '',
                        '📊 Overall Statistics:',
                        f"  • Total EOs processed: {result.get('stats', {}).get('total_eos', 0)}",
                        f"  • Total converters found: {result.get('stats', {}).get('total_converters', 0)}",
                        f"  • Created: {result.get('stats', {}).get('created', 0)}",
                        f"  • Updated: {result.get('stats', {}).get('updated', 0)}",
                        '',
                        '=' * 80,
                        '',
                    ]

                    # Add detailed logs from each worker
                    for detail in batch_details:
                        batch_num = detail.get('batch_number', '?')
                        eo_count = detail.get('eo_count', 0)
                        stats = detail.get('stats', {})
                        logs = detail.get('logs', [])

                        # Add worker header
                        output.append(f"👷 Worker {batch_num} [COMPLETED] - Processed {eo_count} EO numbers")
                        output.append('-' * 80)
                        output.append(f"  📊 Results: {stats.get('total_converters', 0)} converters | Created: {stats.get('created', 0)} | Updated: {stats.get('updated', 0)}")
                        output.append('')

                        # Add worker logs
                        if logs:
                            for log_line in logs:
                                output.append(f"  {log_line}")
                        else:
                            output.append(f"  Processed {eo_count} EOs → {stats.get('total_converters', 0)} converters")

                        output.append('')  # Empty line between workers

                    output.append('=' * 80)

                    return JsonResponse({
                        'status': 'completed',
                        'output': output,
                        'stats': result.get('stats', {}),
                        'message': 'Parallel scraping completed successfully',
                        'workers': [],  # Workers are done, no need to show progress
                        'error': None,
                    })
                else:
                    # Workers still running - fetch individual worker progress
                    workers_progress = []

                    for i, (worker_id, info) in enumerate(zip(worker_task_ids, worker_info)):
                        worker_result = AsyncResult(worker_id)
                        worker_state = worker_result.state

                        # Build worker progress info
                        worker_data = {
                            'worker_number': info.get('batch_number', i + 1),
                            'task_id': worker_id,
                            'state': worker_state,
                            'eo_numbers': info.get('eo_numbers', []),
                            'eo_count': info.get('eo_count', 0),
                            'output': [],
                            'progress': 0,
                            'current': 0,
                            'total': info.get('eo_count', 0),
                        }

                        if worker_state == 'PROGRESS':
                            # Get progress information from task meta
                            worker_meta = worker_result.info or {}

                            # Get logs from task meta
                            logs = worker_meta.get('logs', [])
                            if logs:
                                worker_data['output'] = logs
                            else:
                                worker_data['output'] = [
                                    f"Status: {worker_meta.get('status', 'Processing...')}",
                                    f"Progress: {worker_meta.get('current', 0)}/{worker_meta.get('total', 0)}",
                                ]

                            worker_data['current'] = worker_meta.get('current', 0)
                            worker_data['total'] = worker_meta.get('total', info.get('eo_count', 0))
                            if worker_data['total'] > 0:
                                worker_data['progress'] = int((worker_data['current'] / worker_data['total']) * 100)
                        elif worker_state == 'SUCCESS':
                            # Worker completed
                            worker_result_data = worker_result.result or {}
                            stats = worker_result_data.get('stats', {})
                            logs = worker_result_data.get('logs', [])

                            if logs:
                                # Show the last few logs plus completion summary
                                worker_data['output'] = logs[-10:] + [
                                    '',
                                    '✅ Completed',
                                    f"Total converters: {stats.get('total_converters', 0)}",
                                    f"Created: {stats.get('created', 0)}, Updated: {stats.get('updated', 0)}",
                                ]
                            else:
                                worker_data['output'] = [
                                    '✅ Completed',
                                    f"Total converters: {stats.get('total_converters', 0)}",
                                    f"Created: {stats.get('created', 0)}, Updated: {stats.get('updated', 0)}",
                                ]

                            worker_data['progress'] = 100
                            worker_data['current'] = worker_data['total']
                        elif worker_state == 'FAILURE':
                            # Worker failed
                            worker_data['output'] = [
                                '❌ Failed',
                                f"Error: {str(worker_result.info)[:100]}"
                            ]
                            worker_data['progress'] = 0
                        elif worker_state == 'PENDING':
                            worker_data['output'] = ['⏳ Waiting to start...']
                            worker_data['progress'] = 0
                        else:
                            worker_data['output'] = [f'Status: {worker_state}']
                            worker_data['progress'] = 0

                        workers_progress.append(worker_data)

                    # Build summary output
                    completed = sum(1 for w in workers_progress if w['state'] == 'SUCCESS')
                    running = sum(1 for w in workers_progress if w['state'] == 'PROGRESS')
                    pending = sum(1 for w in workers_progress if w['state'] == 'PENDING')
                    failed = sum(1 for w in workers_progress if w['state'] == 'FAILURE')

                    output = [
                        '⚡ Parallel scraping in progress...',
                        '',
                        f"📊 Workers: {len(workers_progress)} total | ✅ {completed} completed | ⏳ {running} running | 🕒 {pending} pending | ❌ {failed} failed",
                        f"🎯 Total EOs: {cached_data.get('total_eos', 'Unknown')}",
                        '',
                        '=' * 80,
                        '',
                    ]

                    # Add logs from all workers
                    for worker in workers_progress:
                        worker_num = worker['worker_number']
                        worker_state = worker['state']
                        worker_logs = worker.get('output', [])

                        # Add worker header
                        output.append(f"👷 Worker {worker_num} [{worker_state}] - Processing {worker['eo_count']} EO numbers")
                        output.append('-' * 80)

                        # Add worker logs
                        if worker_logs:
                            for log_line in worker_logs:
                                output.append(f"  {log_line}")
                        else:
                            output.append("  No logs yet...")

                        output.append('')  # Empty line between workers

                    output.append('=' * 80)
                    output.append('')
                    output.append('💡 Tip: Scroll down to see individual worker cards with detailed progress.')

                    return JsonResponse({
                        'status': 'running',
                        'output': output,
                        'current_status': 'Workers processing data in parallel',
                        'workers': workers_progress,
                        'error': None,
                    })

        # Regular task monitoring (non-parallel)
        task_result = AsyncResult(task_id)

        # Build response based on task state
        response = {
            'status': task_result.state,
            'task_id': task_id,
        }

        if task_result.state == 'PENDING':
            response.update({
                'status': 'pending',
                'output': ['Task is waiting to start...'],
                'error': None,
            })
        elif task_result.state == 'PROGRESS':
            # Get progress information from task meta
            info = task_result.info
            response.update({
                'status': 'running',
                'output': info.get('output', []),
                'current': info.get('current', 0),
                'total': info.get('total', 100),
                'current_status': info.get('status', 'Running...'),
                'error': None,
            })
        elif task_result.state == 'SUCCESS':
            # Task completed successfully
            result = task_result.result
            response.update({
                'status': 'completed',
                'output': result.get('output', []),
                'stats': result.get('stats', {}),
                'message': result.get('message', 'Scraping completed successfully'),
                'error': None,
            })
        elif task_result.state == 'FAILURE':
            # Task failed
            info = task_result.info
            response.update({
                'status': 'error',
                'output': info.get('output', []) if isinstance(info, dict) else [],
                'error': str(task_result.info) if not isinstance(info, dict) else info.get('error', str(task_result.info)),
            })
        else:
            # Other states (RETRY, REVOKED, etc.)
            response.update({
                'status': task_result.state.lower(),
                'output': ['Task status: ' + task_result.state],
                'error': None,
            })

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': f'Error retrieving task status: {str(e)}',
            'output': [],
        }, status=500)


@staff_member_required
def run_parallel_scraper(request):
    """
    Trigger parallel website scraping operation with multiple workers
    """
    if request.method == 'POST':
        num_workers = request.POST.get('num_workers', '4')
        headless = request.POST.get('headless') == 'true'
        pages = request.POST.get('pages', '').strip()
        test_mode = request.POST.get('test_mode', 'false') == 'true'
        eo_numbers = request.POST.get('eo_numbers', '').strip()
        scheduled_time_raw = request.POST.get('scheduled_time', '').strip()

        try:
            # Convert num_workers to int
            try:
                num_workers_int = int(num_workers) if num_workers and num_workers.strip() else 4
            except (ValueError, AttributeError) as e:
                messages.error(request, f'Invalid number of workers: "{num_workers}". Please enter a valid number.')
                return redirect('admin:scraper_dashboard')

            # Validate num_workers range
            if num_workers_int < 1 or num_workers_int > 10:
                messages.error(request, 'Number of workers must be between 1 and 50.')
                return redirect('admin:scraper_dashboard')

            # Convert pages to int if provided
            try:
                pages_int = int(pages) if pages and pages.strip() else 50  # Default to 50
            except (ValueError, AttributeError) as e:
                messages.error(request, f'Invalid pages value: "{pages}". Please enter a valid number.')
                return redirect('admin:scraper_dashboard')

            # Parse scheduled datetime (optional)
            try:
                scheduled_time = parse_scheduled_datetime(scheduled_time_raw)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('admin:scraper_dashboard')

            task_kwargs = {
                'num_workers': num_workers_int,
                'headless': headless,
                'pages': pages_int,
                'test_mode': test_mode,
                'eo_numbers': eo_numbers if eo_numbers else None,
            }

            # Launch Celery task
            if scheduled_time and scheduled_time > timezone.now():
                eta = scheduled_time.astimezone(timezone.utc)
                task = parallel_scrape_website.apply_async(kwargs=task_kwargs, eta=eta)
                display_time = timezone.localtime(scheduled_time).strftime('%B %d, %Y %I:%M %p %Z')
                messages.success(
                    request,
                    f'Parallel scraping with {num_workers_int} workers scheduled for {display_time}. '
                    f'Task ID: {task.id}. The task will start automatically at the scheduled time.'
                )
                return redirect('admin:scraper_dashboard')
            else:
                task = parallel_scrape_website.delay(**task_kwargs)
                parent_task_id = task.id

                # Monitor the parent task which contains worker info
                progress_url = f"{reverse('admin:scraper_progress')}?task_id={parent_task_id}&type=parallel"
                note = ''
                if scheduled_time:
                    note = ' (requested schedule was in the past, so it started immediately)'
                messages.success(
                    request,
                    f'Parallel scraping with {num_workers_int} workers started! Task ID: {parent_task_id}{note}'
                )

                # Redirect to progress page to monitor workers
                return redirect(progress_url)

        except ValueError as e:
            messages.error(request, f'Invalid input: {str(e)}. Please check your values.')
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            messages.error(request, f'Error starting parallel scraping task: {str(e)}')
            # Log the full traceback for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Parallel scraper error: {error_details}")

        return redirect('admin:scraper_dashboard')

    return redirect('admin:scraper_dashboard')
