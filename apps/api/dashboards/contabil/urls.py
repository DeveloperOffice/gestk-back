from rest_framework.routers import DefaultRouter
from .views import ContabilViewSet

router = DefaultRouter()
router.register(r'', ContabilViewSet, basename='contabil')

urlpatterns = router.urls
