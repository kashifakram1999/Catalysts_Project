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
    eo_document_url = serializers.CharField(read_only=True)

    class Meta:
        model = CatalyticConverter
        fields = [
            'id',
            'executive_order',
            'eo_document_url',
            'manufacturer_name',
            'series_model',
            'make',
            'model',
            'year_range',
            'model_year_start',
            'model_year_end',
            'vehicle_class',
            'eo_date',
        ]


class CatalyticConverterDetailSerializer(serializers.ModelSerializer):
    """Serializer for converter detail view"""
    manufacturer = ManufacturerSerializer(read_only=True)
    manufacturer_name = serializers.CharField(source='manufacturer.name', read_only=True)
    year_range = serializers.CharField(read_only=True)
    eo_document_url = serializers.CharField(read_only=True)

    class Meta:
        model = CatalyticConverter
        fields = [
            'id',
            'executive_order',
            'eo_document_url',
            'manufacturer',
            'manufacturer_name',
            'series_model',
            'make',
            'model',
            'year_range',
            'model_year_start',
            'model_year_end',
            'vehicle_class',
            'eo_date',
        ]


class SearchStatsSerializer(serializers.Serializer):
    """Serializer for search statistics"""
    total_converters = serializers.IntegerField()
    total_manufacturers = serializers.IntegerField()
    unique_makes = serializers.IntegerField()
    year_range = serializers.DictField()
    latest_eo_date = serializers.DateField()
