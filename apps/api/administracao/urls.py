"""
URLs para API de Administração
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContratoGestkViewSet, UsuarioAcessoViewSet, 
    ContabilidadeAdministracaoViewSet
)

router = DefaultRouter()
router.register(r'contratos-gestk', ContratoGestkViewSet, basename='contratogestk')
router.register(r'usuarios-acesso', UsuarioAcessoViewSet, basename='usuarioacesso')
router.register(r'contabilidades-admin', ContabilidadeAdministracaoViewSet, basename='contabilidade-admin')

urlpatterns = [
    path('', include(router.urls)),
]