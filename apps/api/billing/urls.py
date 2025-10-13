"""
URLs para API de Billing
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PlanoViewSet, AssinaturaViewSet, FaturaViewSet, 
    PagamentoViewSet, ContabilidadeBillingViewSet
)

router = DefaultRouter()
router.register(r'planos', PlanoViewSet, basename='plano')
router.register(r'assinaturas', AssinaturaViewSet, basename='assinatura')
router.register(r'faturas', FaturaViewSet, basename='fatura')
router.register(r'pagamentos', PagamentoViewSet, basename='pagamento')
router.register(r'contabilidades-billing', ContabilidadeBillingViewSet, basename='contabilidade-billing')

urlpatterns = [
    path('', include(router.urls)),
    path('superuser/', include('apps.api.billing.superuser.urls')),
]
