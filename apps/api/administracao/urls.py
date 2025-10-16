"""
URLs para API de Administração
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UsuarioAcessoViewSet, 
    ContabilidadeAdministracaoViewSet
)

# Nota: ContratoGestkViewSet foi consolidado em /api/gestao/superuser/contratos-gestk/
# para evitar duplicação de endpoints

router = DefaultRouter()
router.register(r'usuarios-acesso', UsuarioAcessoViewSet, basename='usuarioacesso')
router.register(r'contabilidades-admin', ContabilidadeAdministracaoViewSet, basename='contabilidade-admin')

urlpatterns = [
    path('', include(router.urls)),
]