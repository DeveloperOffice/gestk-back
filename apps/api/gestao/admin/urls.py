"""
URLs para módulo Admin de Gestão
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .usuario_views import UsuarioViewSet
from .contrato_views import ContratoViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='admin-usuarios')
router.register(r'contratos', ContratoViewSet, basename='admin-contratos')

urlpatterns = [
    path('', include(router.urls)),
]
