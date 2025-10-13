"""
URLs para billing SUPERUSER
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .assinatura_views import AssinaturaViewSet
from .fatura_views import FaturaViewSet

# Router
router = DefaultRouter()
router.register(r'assinaturas', AssinaturaViewSet, basename='assinaturas')
router.register(r'faturas', FaturaViewSet, basename='faturas')

urlpatterns = [
    path('', include(router.urls)),
]
