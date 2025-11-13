"""
Django REST Framework serializers for catalytic converter data
"""

from rest_framework import serializers
from .models import Manufacturer, CatalyticConverter


class ManufacturerSerializer(serializers.ModelSerializer):
    """Serializer for Manufacturer model"""
    converter_count = serializers.SerializerMethodField()

    class Meta:
        model = Manufacturer
        fields = ['id', 'name', 'contact_info', 'converter_count']

    def get_converter_count(self, obj):
        return obj.converters.filter(is_active=True).count()


class CatalyticConverterListSerializer(serializers.ModelSerializer):
    """Serializer for converter list view (minimal fields)"""
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    year_range = serializers.CharField(read_only=True)

    class Meta:
        model = CatalyticConverter
        fields = [
            'id',
            'executive_order',
            'manufacturer_name',
            'series_model',
            'make',
            'model',
            'year_range',
            'model_year_start',
            'model_year_end',
            'engine_size',
            'vehicle_class',
            'application_type',
            'converter_location',
            'converter_type',
            'quantity',
            'cert_level',
            'test_group',
            'eo_date',
        ]


class CatalyticConverterDetailSerializer(serializers.ModelSerializer):
    """Serializer for converter detail view (all fields)"""
    manufacturer = ManufacturerSerializer(read_only=True)
    year_range = serializers.CharField(read_only=True)

    class Meta:
        model = CatalyticConverter
        fields = '__all__'


class SearchStatsSerializer(serializers.Serializer):
    """Serializer for search statistics"""
    total_converters = serializers.IntegerField()
    total_manufacturers = serializers.IntegerField()
    unique_makes = serializers.IntegerField()
    year_range = serializers.DictField()
    latest_eo_date = serializers.DateField()
