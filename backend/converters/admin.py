from django.contrib import admin
from .models import Manufacturer, CatalyticConverter


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at', 'updated_at']
    search_fields = ['name']
    list_filter = ['created_at']
    ordering = ['name']


@admin.register(CatalyticConverter)
class CatalyticConverterAdmin(admin.ModelAdmin):
    list_display = [
        'executive_order',
        'manufacturer',
        'make',
        'model_year_start',
        'model_year_end',
        'product_name',
        'eo_date',
        'is_active'
    ]
    list_filter = [
        'is_active',
        'manufacturer',
        'make',
        'vehicle_class',
        'application_type',
        'eo_date',
    ]
    search_fields = [
        'executive_order',
        'product_name',
        'make',
        'model',
        'test_group',
    ]
    ordering = ['-eo_date', 'make']
    date_hierarchy = 'eo_date'

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'manufacturer',
                'executive_order',
                'product_name',
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
                'engine_size',
            )
        }),
        ('Technical Specifications', {
            'fields': (
                'test_group',
                'cert_level',
                'application_type',
                'converter_location',
                'converter_type',
                'quantity',
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
