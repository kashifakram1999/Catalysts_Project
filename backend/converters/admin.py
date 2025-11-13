from django.contrib import admin
from .models import Manufacturer, CatalyticConverter


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_info', 'created_at', 'updated_at']
    search_fields = ['name', 'contact_info']
    list_filter = ['created_at']
    ordering = ['name']


@admin.register(CatalyticConverter)
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
