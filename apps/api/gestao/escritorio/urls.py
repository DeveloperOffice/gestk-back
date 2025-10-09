from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EscritorioViewSet

# Router para ViewSets
router = DefaultRouter()
router.register(r'', EscritorioViewSet, basename='escritorio')

urlpatterns = [
    # Incluir rotas do router
] + router.urls