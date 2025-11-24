"""
API Views for catalytic converter data
"""

from rest_framework import viewsets, filters, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Min, Max, Count
from .models import Manufacturer, CatalyticConverter, BlogPost
from .serializers import (
    ManufacturerSerializer,
    CatalyticConverterListSerializer,
    CatalyticConverterDetailSerializer,
    SearchStatsSerializer,
    BlogPostSerializer,
)


class ManufacturerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for manufacturers
    """
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name']
    ordering = ['name']


class CatalyticConverterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for catalytic converters with advanced filtering
    """
    queryset = CatalyticConverter.objects.select_related('manufacturer').filter(is_active=True)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'executive_order',
        'make',
        'model',
        'manufacturer__name',
        'series_model',
    ]
    ordering_fields = [
        'make',
        'model_year_start',
        'eo_date',
        'manufacturer__name',
    ]
    ordering = ['-eo_date']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CatalyticConverterDetailSerializer
        return CatalyticConverterListSerializer

    def _get_filter_params(self, exclude_keys=None):
        """
        Build a dictionary of query params excluding empty values and optional keys
        """
        exclude = set(exclude_keys or [])
        params = {}
        for key, value in self.request.query_params.items():
            if key in exclude:
                continue
            if value not in (None, ''):
                params[key] = value
        return params

    def filter_queryset_by_params(self, queryset, params):
        """
        Apply filtering logic shared by list and filter helper endpoints
        """
        params = params or {}

        year = params.get('year')
        year_min = params.get('year_min')
        year_max = params.get('year_max')

        if year:
            try:
                year = int(year)
                queryset = queryset.filter(
                    model_year_start__lte=year,
                    model_year_end__gte=year
                )
            except ValueError:
                pass

        if year_min:
            try:
                queryset = queryset.filter(model_year_end__gte=int(year_min))
            except ValueError:
                pass

        if year_max:
            try:
                queryset = queryset.filter(model_year_start__lte=int(year_max))
            except ValueError:
                pass

        make = params.get('make')
        if make:
            queryset = queryset.filter(make__iexact=make)

        model = params.get('model')
        if model:
            queryset = queryset.filter(model__icontains=model)

        vehicle_class = params.get('vehicle_class')
        if vehicle_class:
            queryset = queryset.filter(vehicle_class__iexact=vehicle_class)

        manufacturer = params.get('manufacturer')
        if manufacturer:
            queryset = queryset.filter(
                Q(manufacturer__id=manufacturer) |
                Q(manufacturer__name__icontains=manufacturer)
            )

        executive_order = params.get('executive_order')
        if executive_order:
            queryset = queryset.filter(executive_order__icontains=executive_order)

        series_model = params.get('series_model')
        if series_model:
            queryset = queryset.filter(series_model__icontains=series_model)

        engine_size = params.get('engine_size')
        if engine_size:
            queryset = queryset.filter(engine_size__icontains=engine_size)

        test_group = params.get('test_group')
        if test_group:
            queryset = queryset.filter(test_group__icontains=test_group)

        application_type = params.get('application_type')
        if application_type:
            queryset = queryset.filter(application_type__icontains=application_type)

        converter_type = params.get('converter_type')
        if converter_type:
            queryset = queryset.filter(converter_type__icontains=converter_type)

        return queryset

    def get_queryset(self):
        """
        Filter queryset based on query parameters
        """
        base_queryset = super().get_queryset()
        params = self._get_filter_params()
        return self.filter_queryset_by_params(base_queryset, params)

    @action(detail=False, methods=['get'])
    def makes(self, request):
        """Get list of unique vehicle makes"""
        makes = CatalyticConverter.objects.filter(
            is_active=True,
            make__isnull=False
        ).exclude(
            make=''
        ).values_list(
            'make', flat=True
        ).distinct().order_by('make')

        return Response(list(makes))

    @action(detail=False, methods=['get'])
    def models(self, request):
        """Get list of models for a specific make"""
        make = request.query_params.get('make')
        if not make:
            return Response(
                {'error': 'Make parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        models = CatalyticConverter.objects.filter(
            is_active=True,
            make__iexact=make,
            model__isnull=False
        ).exclude(
            model=''
        ).values_list(
            'model', flat=True
        ).distinct().order_by('model')

        return Response(list(models))

    @action(detail=False, methods=['get'])
    def years(self, request):
        """Get available year range"""
        base_queryset = super().get_queryset()
        params = self._get_filter_params(exclude_keys=['year', 'year_min', 'year_max'])
        queryset = self.filter_queryset_by_params(base_queryset, params)

        year_range = queryset.aggregate(
            min_year=Min('model_year_start'),
            max_year=Max('model_year_end')
        )

        if year_range['min_year'] and year_range['max_year']:
            years = list(range(year_range['min_year'], year_range['max_year'] + 1))
            return Response({
                'years': years,
                'min': year_range['min_year'],
                'max': year_range['max_year']
            })
        return Response({'years': [], 'min': None, 'max': None})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get database statistics"""
        stats = {
            'total_converters': CatalyticConverter.objects.filter(is_active=True).count(),
            'total_manufacturers': Manufacturer.objects.count(),
            'unique_makes': CatalyticConverter.objects.filter(
                is_active=True,
                make__isnull=False
            ).exclude(make='').values('make').distinct().count(),
            'year_range': CatalyticConverter.objects.filter(
                is_active=True
            ).aggregate(
                min=Min('model_year_start'),
                max=Max('model_year_end')
            ),
            'latest_eo_date': CatalyticConverter.objects.filter(
                is_active=True,
                eo_date__isnull=False
            ).aggregate(Max('eo_date'))['eo_date__max']
        }

        return Response(stats)

    @action(detail=False, methods=['get'])
    def filters(self, request):
        """Get all available filter options"""
        base_queryset = super().get_queryset()

        def filtered_queryset(exclude_keys=None):
            params = self._get_filter_params(exclude_keys=exclude_keys)
            return self.filter_queryset_by_params(base_queryset, params)

        makes_qs = filtered_queryset(exclude_keys=['make'])
        vehicle_class_qs = filtered_queryset(exclude_keys=['vehicle_class'])
        manufacturer_qs = filtered_queryset(exclude_keys=['manufacturer'])
        executive_order_qs = filtered_queryset(exclude_keys=['executive_order'])
        series_model_qs = filtered_queryset(exclude_keys=['series_model'])
        engine_size_qs = filtered_queryset(exclude_keys=['engine_size'])
        test_group_qs = filtered_queryset(exclude_keys=['test_group'])
        application_type_qs = filtered_queryset(exclude_keys=['application_type'])
        converter_type_qs = filtered_queryset(exclude_keys=['converter_type'])
        years_qs = filtered_queryset(exclude_keys=['year', 'year_min', 'year_max'])

        manufacturers = manufacturer_qs.filter(
            manufacturer__isnull=False
        ).values(
            'manufacturer_id',
            'manufacturer__name'
        ).distinct().order_by('manufacturer__name')

        year_range = years_qs.aggregate(
            min_year=Min('model_year_start'),
            max_year=Max('model_year_end')
        )

        years = []
        if year_range['min_year'] is not None and year_range['max_year'] is not None:
            years = list(range(year_range['min_year'], year_range['max_year'] + 1))

        filters_data = {
            'makes': list(makes_qs.filter(
                make__isnull=False
            ).exclude(make='').values_list('make', flat=True).distinct().order_by('make')),
            'vehicle_classes': list(vehicle_class_qs.filter(
                vehicle_class__isnull=False
            ).exclude(vehicle_class='').values_list('vehicle_class', flat=True).distinct().order_by('vehicle_class')),
            'manufacturers': [
                {'id': item['manufacturer_id'], 'name': item['manufacturer__name']}
                for item in manufacturers if item['manufacturer_id'] is not None
            ],
            'executive_orders': list(executive_order_qs.filter(
                executive_order__isnull=False
            ).exclude(executive_order='').values_list('executive_order', flat=True).distinct().order_by('executive_order')),
            'series_models': list(series_model_qs.filter(
                series_model__isnull=False
            ).exclude(series_model='').values_list('series_model', flat=True).distinct().order_by('series_model')),
            'engine_sizes': list(engine_size_qs.filter(
                engine_size__isnull=False
            ).exclude(engine_size='').values_list('engine_size', flat=True).distinct().order_by('engine_size')),
            'test_groups': list(test_group_qs.filter(
                test_group__isnull=False
            ).exclude(test_group='').values_list('test_group', flat=True).distinct().order_by('test_group')),
            'application_types': list(application_type_qs.filter(
                application_type__isnull=False
            ).exclude(application_type='').values_list('application_type', flat=True).distinct().order_by('application_type')),
            'converter_types': list(converter_type_qs.filter(
                converter_type__isnull=False
            ).exclude(converter_type='').values_list('converter_type', flat=True).distinct().order_by('converter_type')),
            'years': years,
            'min_year': year_range['min_year'],
            'max_year': year_range['max_year'],
        }

        return Response(filters_data)


class BlogPostViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for published blog posts"""

    queryset = BlogPost.objects.filter(is_published=True).order_by('-published_at')
    serializer_class = BlogPostSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
    lookup_field = 'slug'
    lookup_value_regex = '[^/]+'

    @action(detail=False, methods=['get'])
    def latest(self, request):
        post = self.get_queryset().first()
        if not post:
            return Response(status=status.HTTP_204_NO_CONTENT)
        serializer = self.get_serializer(post)
        return Response(serializer.data)
