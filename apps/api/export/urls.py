from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ExportViewSet

# Router para ViewSets
router = DefaultRouter()
router.register(r'', ExportViewSet, basename='export')

urlpatterns = [
    # Incluir rotas do router
] + router.urls