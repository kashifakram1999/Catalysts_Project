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
from .tasks import scrape_pdf_task, scrape_website_task


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

    if not task_id:
        return JsonResponse({'error': 'No task_id provided'}, status=400)

    try:
        # Get Celery task result
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
