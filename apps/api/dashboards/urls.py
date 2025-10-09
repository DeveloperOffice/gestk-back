from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DemograficoViewSet, FiscalViewSet, ContabilViewSet, IndicadoresViewSet, DREViewSet
from .organizacional.views import OrganizacionalViewSet
from .pessoal.views import PessoalViewSet

# Router para ViewSets
router = DefaultRouter()
router.register(r'demografico', DemograficoViewSet, basename='demografico')
router.register(r'fiscal', FiscalViewSet, basename='fiscal')
router.register(r'contabil', ContabilViewSet, basename='contabil')
router.register(r'indicadores', IndicadoresViewSet, basename='indicadores')
router.register(r'dre', DREViewSet, basename='dre')
router.register(r'organizacional', OrganizacionalViewSet, basename='organizacional')
router.register(r'pessoal', PessoalViewSet, basename='pessoal')

urlpatterns = [
    # Módulos específicos seguindo a estrutura da documentação
    path('demografico/', include('apps.api.dashboards.demografico.urls')),
    # Incluir rotas do router
] + router.urls