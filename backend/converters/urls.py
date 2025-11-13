"""
URL routing for converters API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ManufacturerViewSet, CatalyticConverterViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')
router.register(r'converters', CatalyticConverterViewSet, basename='converter')

urlpatterns = [
    path('', include(router.urls)),
]
