from rest_framework.routers import DefaultRouter
from .views import FiscalViewSet

router = DefaultRouter()
router.register(r'', FiscalViewSet, basename='fiscal')

urlpatterns = router.urls
