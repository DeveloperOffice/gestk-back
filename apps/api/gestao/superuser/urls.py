"""
URLs para gestão SUPERUSER
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ContabilidadeViewSet
from .contrato_gestk_views import ContratoGestkViewSet

# Router
router = DefaultRouter()
router.register(r'contabilidades', ContabilidadeViewSet, basename='contabilidades')
router.register(r'contratos-gestk', ContratoGestkViewSet, basename='contratos-gestk')

urlpatterns = [
    path('', include(router.urls)),
]
