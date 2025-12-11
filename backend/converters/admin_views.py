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
from .tasks import scrape_website_task, parallel_scrape_website  # scrape_pdf_task - removed (no longer needed)


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


def _get_admin_site():
    """
    Import the admin site lazily to avoid circular imports when building context.
    """
    from .admin import admin_site  # Local import to prevent circular dependency
    return admin_site


@staff_member_required
def scraper_dashboard(request):
    """
    Main dashboard for scraping operations
    Shows stats and provides buttons to trigger scraping
    """
    admin_context = _get_admin_site().each_context(request)
    context = {
        'title': 'Data Scraping Dashboard',
        'total_converters': CatalyticConverter.objects.count(),
        'total_manufacturers': Manufacturer.objects.count(),
        'active_converters': CatalyticConverter.objects.filter(is_active=True).count(),
        'last_scraped': CatalyticConverter.objects.filter(
            last_scraped__isnull=False
        ).order_by('-last_scraped').first(),
    }
    context.update(admin_context)
    # Ensure templates expecting `app_list` continue to work with the sidebar
    context.setdefault('app_list', admin_context.get('available_apps'))
    return render(request, 'admin/converters/scraper_dashboard.html', context)


# PDF SCRAPER VIEW - COMMENTED OUT (No longer needed)
# @staff_member_required
# def run_pdf_scraper(request):
#     """
#     Trigger PDF scraping operation using Celery
#     """
#     if request.method == 'POST':
#         use_local = request.POST.get('use_local') == 'true'
#         limit = request.POST.get('limit', None)
#         scheduled_time_raw = request.POST.get('scheduled_time', '').strip()

#         try:
#             # Convert limit to int if provided
#             limit_int = int(limit) if limit and limit.strip() else None

#             # Parse scheduled datetime (optional)
#             try:
#                 scheduled_time = parse_scheduled_datetime(scheduled_time_raw)
#             except ValueError as exc:
#                 messages.error(request, str(exc))
#                 return redirect('admin:scraper_dashboard')

#             task_kwargs = {
#                 'use_local': use_local,
#                 'limit': limit_int,
#             }

#             # Launch Celery task
#             if scheduled_time and scheduled_time > timezone.now():
#                 eta = scheduled_time.astimezone(timezone.utc)
#                 task = scrape_pdf_task.apply_async(kwargs=task_kwargs, eta=eta)
#                 progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=pdf"
#                 display_time = timezone.localtime(scheduled_time).strftime('%B %d, %Y %I:%M %p %Z')
#                 messages.success(
#                     request,
#                     f'PDF scraping scheduled for {display_time}. Task ID: {task.id}. '
#                     f'You can monitor it at {progress_url}'
#                 )
#                 return redirect('admin:scraper_dashboard')
#             else:
#                 task = scrape_pdf_task.delay(**task_kwargs)
#                 progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type=pdf"
#                 note = ''
#                 if scheduled_time:
#                     note = ' (requested schedule was in the past, so it started immediately)'
#                 messages.success(
#                     request,
#                     f'PDF scraping task started! Task ID: {task.id}{note}'
#                 )

#                 # Redirect to progress page for live monitoring
#                 return redirect(progress_url)

#         except Exception as e:
#             messages.error(request, f'Error starting PDF scraping task: {str(e)}')

#         return redirect('admin:scraper_dashboard')

#     return redirect('admin:scraper_dashboard')


@staff_member_required
def run_website_scraper(request):
    """
    Trigger website scraping operation using Celery and EO-based scraper
    """
    if request.method == 'POST':
        # Check for concurrent scrapers
        from .models import ScraperRun
        active_scrapers = ScraperRun.objects.filter(status='running').exists()

        if active_scrapers:
            messages.error(
                request,
                'Cannot start scraper: Another scraper is already running. '
                'Please wait for it to complete or stop it first.'
            )
            return redirect('admin:scraper_dashboard')

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
    from .models import ScraperRun

    task_id = request.GET.get('task_id')
    scraper_type = request.GET.get('type', 'unknown')

    if not task_id:
        return JsonResponse({'error': 'No task_id provided'}, status=400)

    # Try to get scraper_run_id from database
    scraper_run_id = None
    try:
        scraper_run = ScraperRun.objects.get(task_id=task_id)
        scraper_run_id = scraper_run.id
    except ScraperRun.DoesNotExist:
        pass

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
                    'scraper_run_id': scraper_run_id,
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
                        'scraper_run_id': scraper_run_id,
                    })

                # Check if scraper_run status overrides task state (for stopped/completed)
                if scraper_run_id:
                    try:
                        scraper_run = ScraperRun.objects.get(id=scraper_run_id)
                        if scraper_run.status in ['stopped', 'completed', 'failed']:
                            # ScraperRun status takes precedence
                            return JsonResponse({
                                'status': scraper_run.status,
                                'task_id': task_id,
                                'scraper_run_id': scraper_run_id,
                                'output': [f'Scraper {scraper_run.status}'],
                                'error': scraper_run.error_message if scraper_run.status == 'failed' else None,
                                'workers': [],  # Empty workers for stopped state
                            })
                    except ScraperRun.DoesNotExist:
                        pass

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
                        'scraper_run_id': scraper_run_id,
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
                        'scraper_run_id': scraper_run_id,
                    })

        # Regular task monitoring (non-parallel)
        task_result = AsyncResult(task_id)

        # Check if scraper_run status overrides task state (for stopped/completed)
        if scraper_run_id:
            try:
                scraper_run = ScraperRun.objects.get(id=scraper_run_id)
                if scraper_run.status in ['stopped', 'completed', 'failed']:
                    # ScraperRun status takes precedence
                    return JsonResponse({
                        'status': scraper_run.status,
                        'task_id': task_id,
                        'scraper_run_id': scraper_run_id,
                        'output': [f'Scraper {scraper_run.status}'],
                        'error': scraper_run.error_message if scraper_run.status == 'failed' else None,
                    })
            except ScraperRun.DoesNotExist:
                pass

        # Build response based on task state
        response = {
            'status': task_result.state,
            'task_id': task_id,
            'scraper_run_id': scraper_run_id,
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
        # Check for concurrent scrapers
        from .models import ScraperRun
        active_scrapers = ScraperRun.objects.filter(status='running').exists()

        if active_scrapers:
            messages.error(
                request,
                'Cannot start scraper: Another scraper is already running. '
                'Please wait for it to complete or stop it first.'
            )
            return redirect('admin:scraper_dashboard')

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
            if num_workers_int < 1 or num_workers_int > 50:
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


@staff_member_required
def check_active_scrapers_api(request):
    """
    API endpoint to check if there are any active or stopped scraper runs
    Returns list of active scrapers and most recent stopped scraper
    """
    from .models import ScraperRun

    try:
        # Get all running scrapers
        active_scrapers = ScraperRun.objects.filter(status='running').order_by('-started_at')

        scrapers_data = []
        for scraper in active_scrapers:
            scrapers_data.append({
                'id': scraper.id,
                'task_id': scraper.task_id,
                'scraper_type': scraper.scraper_type,
                'status': scraper.status,
                'progress_percentage': scraper.progress_percentage,
                'processed_count': scraper.processed_count,
                'total_eo_count': scraper.total_eo_count,
                'started_at': scraper.started_at.isoformat(),
            })

        # Get most recent stopped scraper
        stopped_scraper = ScraperRun.objects.filter(status='stopped').order_by('-stopped_at').first()
        stopped_data = None
        if stopped_scraper:
            remaining = len(stopped_scraper.remaining_eo_numbers)
            current_eo = stopped_scraper.current_eo_number
            current_page = stopped_scraper.current_page_number
            stopped_data = {
                'id': stopped_scraper.id,
                'task_id': stopped_scraper.task_id,
                'scraper_type': stopped_scraper.scraper_type,
                'progress_percentage': stopped_scraper.progress_percentage,
                'processed_count': stopped_scraper.processed_count,
                'total_eo_count': stopped_scraper.total_eo_count,
                'remaining_count': remaining,
                'current_eo': current_eo,
                'current_page': current_page,
                'stopped_at': stopped_scraper.stopped_at.isoformat() if stopped_scraper.stopped_at else None,
            }

        return JsonResponse({
            'active_scrapers': scrapers_data,
            'has_active': len(scrapers_data) > 0,
            'stopped_scraper': stopped_data,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def stop_scraper_api(request):
    """
    API endpoint to request a scraper to stop gracefully
    """
    from .models import ScraperRun

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        scraper_run_id = data.get('scraper_run_id')

        if not scraper_run_id:
            return JsonResponse({'error': 'scraper_run_id is required'}, status=400)

        try:
            scraper_run = ScraperRun.objects.get(id=scraper_run_id)

            if scraper_run.status != 'running':
                return JsonResponse({
                    'error': f'Scraper is not running (current status: {scraper_run.status})'
                }, status=400)

            # Request stop
            scraper_run.request_stop()

            return JsonResponse({
                'success': True,
                'message': 'Stop requested. The scraper will stop gracefully after completing the current EO.',
                'scraper_run_id': scraper_run.id,
            })

        except ScraperRun.DoesNotExist:
            return JsonResponse({'error': f'ScraperRun {scraper_run_id} not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@staff_member_required
def resume_scraper_api(request):
    """
    API endpoint to resume a stopped scraper from where it left off
    """
    from .models import ScraperRun

    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=400)

    import json
    try:
        data = json.loads(request.body)
        scraper_run_id = data.get('scraper_run_id')

        if not scraper_run_id:
            return JsonResponse({'error': 'scraper_run_id is required'}, status=400)

        try:
            scraper_run = ScraperRun.objects.get(id=scraper_run_id)

            if scraper_run.status != 'stopped':
                return JsonResponse({
                    'error': f'Scraper is not in stopped state (current status: {scraper_run.status})'
                }, status=400)

            # Check if there's work to be done
            remaining_eos = scraper_run.remaining_eo_numbers
            current_eo = scraper_run.current_eo_number
            current_page = scraper_run.current_page_number

            if not remaining_eos and not (current_eo and current_page):
                return JsonResponse({
                    'error': 'No remaining work to resume'
                }, status=400)

            # Launch appropriate task based on scraper type
            # Use the ORIGINAL eo_numbers_to_process list, scraper will handle resume logic
            original_eo_list = scraper_run.eo_numbers_to_process

            if scraper_run.scraper_type == 'parallel':
                task = parallel_scrape_website.delay(
                    num_workers=scraper_run.num_workers,
                    headless=scraper_run.headless,
                    pages=scraper_run.pages_per_eo,
                    test_mode=scraper_run.test_mode,
                    eo_numbers=','.join(original_eo_list),
                )
            else:
                task = scrape_website_task.delay(
                    headless=scraper_run.headless,
                    pages=scraper_run.pages_per_eo,
                    test_mode=scraper_run.test_mode,
                    eo_numbers=','.join(original_eo_list),
                )

            # Update scraper run with new task ID and reset stop flags
            # Keep the original eo_numbers_to_process, current_eo_number, and current_page_number
            # The scraper will use these to resume from the correct position
            scraper_run.task_id = task.id
            scraper_run.status = 'running'
            scraper_run.stop_requested = False
            scraper_run.stopped_at = None
            scraper_run.save(update_fields=['task_id', 'status', 'stop_requested', 'stopped_at', 'updated_at'])

            progress_url = f"{reverse('admin:scraper_progress')}?task_id={task.id}&type={scraper_run.scraper_type}"

            resume_info = f"Resuming from EO {current_eo}, page {current_page}" if current_eo and current_page else f"Resuming with {len(remaining_eos)} remaining EO numbers"

            return JsonResponse({
                'success': True,
                'message': resume_info,
                'task_id': task.id,
                'scraper_run_id': scraper_run.id,
                'progress_url': progress_url,
            })

        except ScraperRun.DoesNotExist:
            return JsonResponse({'error': f'ScraperRun {scraper_run_id} not found'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        return JsonResponse({'error': str(e), 'traceback': traceback.format_exc()}, status=500)


@staff_member_required
def csv_upload_view(request):
    """
    Handle CSV file upload for bulk converter data import
    """
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            return JsonResponse({'error': 'No file uploaded'}, status=400)

        if not csv_file.name.endswith('.csv'):
            return JsonResponse({'error': 'File must be a CSV'}, status=400)

        try:
            import csv
            import io
            from decimal import Decimal, InvalidOperation

            # Read CSV file
            file_data = csv_file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(file_data))

            # Validate headers
            required_headers = [
                'executive_order', 'series_model', 'make', 'model',
                'model_year_start', 'model_year_end', 'vehicle_class',
                'engine_size', 'test_group', 'cert_level', 'application_type',
                'converter_location', 'converter_type', 'quantity', 'eo_date',
                'manufacturer', 'product_name', 'part_number'
            ]

            headers = csv_reader.fieldnames
            missing_headers = [h for h in required_headers if h not in headers]

            if missing_headers:
                return JsonResponse({
                    'error': f'Missing required columns: {", ".join(missing_headers)}'
                }, status=400)

            # Process CSV rows
            created_count = 0
            updated_count = 0
            error_count = 0
            errors = []

            for row_num, row in enumerate(csv_reader, start=2):
                try:
                    # Get or create manufacturer
                    manufacturer_name = row.get('manufacturer', '').strip()
                    if not manufacturer_name:
                        errors.append(f"Row {row_num}: Manufacturer name is required")
                        error_count += 1
                        continue

                    manufacturer, _ = Manufacturer.objects.get_or_create(
                        name=manufacturer_name,
                        defaults={'contact_info': ''}
                    )

                    # Parse date
                    eo_date_str = row.get('eo_date', '').strip()
                    if eo_date_str:
                        try:
                            from datetime import datetime
                            eo_date = datetime.strptime(eo_date_str, '%Y-%m-%d').date()
                        except ValueError:
                            errors.append(f"Row {row_num}: Invalid date format '{eo_date_str}'. Use YYYY-MM-DD")
                            error_count += 1
                            continue
                    else:
                        eo_date = None

                    # Parse quantity
                    quantity_str = row.get('quantity', '1').strip()
                    try:
                        quantity = int(quantity_str) if quantity_str else 1
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid quantity '{quantity_str}'")
                        error_count += 1
                        continue

                    # Parse year fields
                    try:
                        year_start = int(row.get('model_year_start', 0))
                        year_end = int(row.get('model_year_end', 0))
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid year values")
                        error_count += 1
                        continue

                    # Create or update converter
                    executive_order = row.get('executive_order', '').strip()
                    if not executive_order:
                        errors.append(f"Row {row_num}: Executive order is required")
                        error_count += 1
                        continue

                    # Check if converter exists (by executive_order and series_model)
                    series_model = row.get('series_model', '').strip()
                    converter, created = CatalyticConverter.objects.update_or_create(
                        executive_order=executive_order,
                        series_model=series_model,
                        defaults={
                            'manufacturer': manufacturer,
                            'part_number': row.get('part_number', '').strip(),
                            'product_name': row.get('product_name', '').strip(),
                            'model_year_start': year_start,
                            'model_year_end': year_end,
                            'make': row.get('make', '').strip(),
                            'model': row.get('model', '').strip(),
                            'vehicle_class': row.get('vehicle_class', '').strip(),
                            'engine_size': row.get('engine_size', '').strip(),
                            'test_group': row.get('test_group', '').strip(),
                            'cert_level': row.get('cert_level', '').strip(),
                            'application_type': row.get('application_type', '').strip(),
                            'converter_location': row.get('converter_location', '').strip(),
                            'converter_type': row.get('converter_type', '').strip(),
                            'quantity': quantity,
                            'eo_date': eo_date,
                            'notes': row.get('notes', '').strip(),
                            'is_active': True,
                            'last_scraped': timezone.now(),
                        }
                    )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    error_count += 1

            # Build response
            response_data = {
                'success': True,
                'created': created_count,
                'updated': updated_count,
                'errors': error_count,
                'total_processed': created_count + updated_count + error_count,
            }

            if errors:
                response_data['error_details'] = errors[:20]  # Limit to first 20 errors
                if len(errors) > 20:
                    response_data['error_details'].append(f"... and {len(errors) - 20} more errors")

            return JsonResponse(response_data)

        except Exception as e:
            import traceback
            return JsonResponse({
                'error': f'Error processing CSV: {str(e)}',
                'traceback': traceback.format_exc()
            }, status=500)

    return JsonResponse({'error': 'POST method required'}, status=400)


@staff_member_required
def download_sample_csv(request):
    """
    Download a sample CSV file with example catalytic converter data
    """
    import os
    from django.http import FileResponse, Http404

    # Path to sample CSV file
    sample_csv_path = os.path.join(
        os.path.dirname(__file__),
        'sample_catalytic_converters.csv'
    )

    if not os.path.exists(sample_csv_path):
        raise Http404("Sample CSV file not found")

    response = FileResponse(
        open(sample_csv_path, 'rb'),
        content_type='text/csv'
    )
    response['Content-Disposition'] = 'attachment; filename="sample_catalytic_converters.csv"'

    return response


@staff_member_required
def export_all_data_csv(request):
    """
    Export all catalytic converter data from the database to CSV
    """
    import csv
    from django.http import HttpResponse

    # Create HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="catalytic_converters_export.csv"'

    # Create CSV writer
    writer = csv.writer(response, lineterminator='\n')

    # Write header row
    writer.writerow([
        'executive_order',
        'series_model',
        'make',
        'model',
        'model_year_start',
        'model_year_end',
        'vehicle_class',
        'engine_size',
        'test_group',
        'cert_level',
        'application_type',
        'converter_location',
        'converter_type',
        'quantity',
        'eo_date',
        'manufacturer',
        'product_name',
        'part_number',
        'notes'
    ])

    # Query all converters from database
    converters = CatalyticConverter.objects.select_related('manufacturer').all()

    # Write data rows
    for converter in converters:
        writer.writerow([
            converter.executive_order or '',
            converter.series_model or '',
            converter.make or '',
            converter.model or '',
            converter.model_year_start or '',
            converter.model_year_end or '',
            converter.vehicle_class or '',
            converter.engine_size or '',
            converter.test_group or '',
            converter.cert_level or '',
            converter.application_type or '',
            converter.converter_location or '',
            converter.converter_type or '',
            converter.quantity or '',
            converter.eo_date.strftime('%Y-%m-%d') if converter.eo_date else '',
            converter.manufacturer.name if converter.manufacturer else '',
            converter.product_name or '',
            converter.part_number or '',
            converter.notes or ''
        ])

    return response
