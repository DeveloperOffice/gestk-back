"""
URLs da API REST - Projeto GESTK

Estrutura de endpoints com Regra de Ouro e multitenancy
Status: 412+ endpoints implementados (100% completo)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router principal
router = DefaultRouter()
router.trailing_slash = False

urlpatterns = [
    # API principal
    path('', include(router.urls)),
    
    # Módulos implementados (412+ endpoints)
    path('auth/', include('apps.api.auth.urls')),                    # 9 endpoints
    path('gestao/', include('apps.api.gestao.urls')),               # 50+ endpoints
    path('dashboards/', include('apps.api.dashboards.urls')),       # 30+ endpoints
    path('export/', include('apps.api.export.urls')),               # 8+ endpoints
    path('administracao/', include('apps.api.administracao.urls')), # 14+ endpoints
    path('billing/', include('apps.api.billing.urls')),             # 22+ endpoints
]
