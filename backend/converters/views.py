"""
API Views for catalytic converter data
"""

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Min, Max, Count
from .models import Manufacturer, CatalyticConverter
from .serializers import (
    ManufacturerSerializer,
    CatalyticConverterListSerializer,
    CatalyticConverterDetailSerializer,
    SearchStatsSerializer
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
        'product_name',
        'make',
        'model',
        'manufacturer__name',
        'test_group',
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

    def get_queryset(self):
        """
        Filter queryset based on query parameters
        """
        queryset = super().get_queryset()

        # Year filtering
        year = self.request.query_params.get('year')
        year_min = self.request.query_params.get('year_min')
        year_max = self.request.query_params.get('year_max')

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

        # Make filtering
        make = self.request.query_params.get('make')
        if make:
            queryset = queryset.filter(make__iexact=make)

        # Model filtering
        model = self.request.query_params.get('model')
        if model:
            queryset = queryset.filter(model__icontains=model)

        # Engine size filtering
        engine_size = self.request.query_params.get('engine_size')
        if engine_size:
            queryset = queryset.filter(engine_size__icontains=engine_size)

        # Vehicle class filtering
        vehicle_class = self.request.query_params.get('vehicle_class')
        if vehicle_class:
            queryset = queryset.filter(vehicle_class__iexact=vehicle_class)

        # Manufacturer filtering
        manufacturer = self.request.query_params.get('manufacturer')
        if manufacturer:
            queryset = queryset.filter(
                Q(manufacturer__id=manufacturer) |
                Q(manufacturer__name__icontains=manufacturer)
            )

        # Application type filtering
        application_type = self.request.query_params.get('application_type')
        if application_type:
            queryset = queryset.filter(application_type__icontains=application_type)

        # Converter type filtering
        converter_type = self.request.query_params.get('converter_type')
        if converter_type:
            queryset = queryset.filter(converter_type__icontains=converter_type)

        # Converter location filtering
        converter_location = self.request.query_params.get('converter_location')
        if converter_location:
            queryset = queryset.filter(converter_location__icontains=converter_location)

        # Test group filtering
        test_group = self.request.query_params.get('test_group')
        if test_group:
            queryset = queryset.filter(test_group__icontains=test_group)

        # Executive order filtering
        executive_order = self.request.query_params.get('executive_order')
        if executive_order:
            queryset = queryset.filter(executive_order__icontains=executive_order)

        # Certification level filtering
        cert_level = self.request.query_params.get('cert_level')
        if cert_level:
            queryset = queryset.filter(cert_level__icontains=cert_level)

        return queryset

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
        year_range = CatalyticConverter.objects.filter(
            is_active=True
        ).aggregate(
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
        filters_data = {
            'makes': list(CatalyticConverter.objects.filter(
                is_active=True,
                make__isnull=False
            ).exclude(make='').values_list('make', flat=True).distinct().order_by('make')),

            'vehicle_classes': list(CatalyticConverter.objects.filter(
                is_active=True,
                vehicle_class__isnull=False
            ).exclude(vehicle_class='').values_list('vehicle_class', flat=True).distinct()),

            'application_types': list(CatalyticConverter.objects.filter(
                is_active=True,
                application_type__isnull=False
            ).exclude(application_type='').values_list('application_type', flat=True).distinct()),

            'converter_locations': list(CatalyticConverter.objects.filter(
                is_active=True,
                converter_location__isnull=False
            ).exclude(converter_location='').values_list('converter_location', flat=True).distinct()),

            'converter_types': list(CatalyticConverter.objects.filter(
                is_active=True,
                converter_type__isnull=False
            ).exclude(converter_type='').values_list('converter_type', flat=True).distinct()),

            'cert_levels': list(CatalyticConverter.objects.filter(
                is_active=True,
                cert_level__isnull=False
            ).exclude(cert_level='').values_list('cert_level', flat=True).distinct()),

            'manufacturers': list(Manufacturer.objects.all().values('id', 'name').order_by('name')),
        }

        return Response(filters_data)
