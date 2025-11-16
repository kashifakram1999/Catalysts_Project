from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import path
from django.utils.html import format_html
from .models import Manufacturer, CatalyticConverter, BlogPost
from . import admin_views


# Custom admin site configuration to add scraper dashboard
class CARBAdminSite(AdminSite):
    """Custom admin site with scraper dashboard"""
    site_header = "CARB Catalytic Converter Admin"
    site_title = "CARB Admin Portal"
    index_title = "Welcome to CARB Catalytic Converter Database"

    # Override the index template
    def index(self, request, extra_context=None):
        """
        Display the main admin index page, with custom scraper dashboard link.
        """
        extra_context = extra_context or {}
        extra_context['show_scraper_dashboard'] = True
        return super().index(request, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('scraper-dashboard/',
                 self.admin_view(admin_views.scraper_dashboard),
                 name='scraper_dashboard'),
            path('scraper-dashboard/run-pdf/',
                 self.admin_view(admin_views.run_pdf_scraper),
                 name='run_pdf_scraper'),
            path('scraper-dashboard/run-website/',
                 self.admin_view(admin_views.run_website_scraper),
                 name='run_website_scraper'),
            path('scraper-dashboard/run-parallel/',
                 self.admin_view(admin_views.run_parallel_scraper),
                 name='run_parallel_scraper'),
            path('scraper-dashboard/stats/',
                 self.admin_view(admin_views.scraper_stats_api),
                 name='scraper_stats_api'),
            path('scraper-dashboard/progress/',
                 self.admin_view(admin_views.scraper_progress_page),
                 name='scraper_progress'),
            path('scraper-dashboard/progress/api/',
                 self.admin_view(admin_views.scraper_progress_api),
                 name='scraper_progress_api'),
        ]
        return custom_urls + urls


# Create instance of custom admin site
admin_site = CARBAdminSite(name='admin')


@admin.register(Manufacturer, site=admin_site)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_info', 'created_at', 'updated_at']
    search_fields = ['name', 'contact_info']
    list_filter = ['created_at']
    ordering = ['name']


@admin.register(CatalyticConverter, site=admin_site)
class CatalyticConverterAdmin(admin.ModelAdmin):
    list_display = [
        'executive_order',
        'manufacturer',
        'series_model',
        'make',
        'model',
        'model_year_start',
        'model_year_end',
        'vehicle_class',
        'test_group',
        'eo_date',
        'is_active'
    ]
    list_filter = [
        'is_active',
        'manufacturer',
        'make',
        'vehicle_class',
        'eo_date',
    ]
    search_fields = [
        'executive_order',
        'series_model',
        'make',
        'model',
        'manufacturer__name',
    ]
    ordering = ['-eo_date', 'make']
    date_hierarchy = 'eo_date'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'manufacturer',
                'executive_order',
                'series_model',
            )
        }),
        ('Vehicle Information', {
            'fields': (
                'make',
                'model',
                'model_year_start',
                'model_year_end',
                'vehicle_class',
            )
        }),
        ('Dates & Status', {
            'fields': (
                'eo_date',
                'is_active',
                'last_scraped',
            )
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ['last_scraped', 'created_at', 'updated_at']

    actions = ['mark_active', 'mark_inactive']

    def mark_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} converter(s) marked as active.')
    mark_active.short_description = "Mark selected converters as active"

    def mark_inactive(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} converter(s) marked as inactive.')
    mark_inactive.short_description = "Mark selected converters as inactive"


@admin.register(BlogPost, site=admin_site)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'is_published', 'published_at', 'updated_at']
    list_filter = ['is_published', 'published_at']
    search_fields = ['title', 'content']
    ordering = ['-published_at']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
