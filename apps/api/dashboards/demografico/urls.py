from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DemograficoViewSet

router = DefaultRouter()
router.register(r'', DemograficoViewSet, basename='demografico')

urlpatterns = router.urls
