"""
URL routing for converters API
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ManufacturerViewSet, CatalyticConverterViewSet, BlogPostViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'manufacturers', ManufacturerViewSet, basename='manufacturer')
router.register(r'converters', CatalyticConverterViewSet, basename='converter')
router.register(r'blogs', BlogPostViewSet, basename='blog')

urlpatterns = [
    path('', include(router.urls)),
]
