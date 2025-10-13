"""
URLs principais dos Dashboards
Inclui todos os 5 dashboards: Demográfico, Organizacional, Pessoal, Contábil e Fiscal
"""
from django.urls import path, include

urlpatterns = [
    path('demografico/', include('apps.api.dashboards.demografico.urls')),
    path('organizacional/', include('apps.api.dashboards.organizacional.urls')),
    path('pessoal/', include('apps.api.dashboards.pessoal.urls')),
    path('contabil/', include('apps.api.dashboards.contabil.urls')),
    path('fiscal/', include('apps.api.dashboards.fiscal.urls')),
]