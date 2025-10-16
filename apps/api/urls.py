"""
URLs da API REST - Projeto GESTK

Estrutura de endpoints com Regra de Ouro e multitenancy
Status: 91 endpoints implementados (83% completo)
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Router principal
router = DefaultRouter()
router.trailing_slash = False

urlpatterns = [
    # API principal
    path('', include(router.urls)),
    
    # Módulos implementados (91 endpoints)
    path('auth/', include('apps.api.auth.urls')),                    # 4 endpoints
    path('gestao/', include('apps.api.gestao.urls')),               # 21 endpoints
    path('dashboards/', include('apps.api.dashboards.urls')),       # 16 endpoints
    path('export/', include('apps.api.export.urls')),               # 4 endpoints
    path('administracao/', include('apps.api.administracao.urls')), # 2 endpoints
    path('billing/', include('apps.api.billing.urls')),             # 44 endpoints
]
