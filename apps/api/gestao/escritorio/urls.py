"""
URLs para API de Escritório
"""

from django.urls import path
from .views import EscritorioViewSet

urlpatterns = [
    path('dashboard/', EscritorioViewSet.as_view({'get': 'dashboard'}), name='escritorio-dashboard'),
]