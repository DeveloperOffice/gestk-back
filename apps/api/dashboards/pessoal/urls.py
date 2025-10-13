from rest_framework.routers import DefaultRouter
from .views import PessoalViewSet

router = DefaultRouter()
router.register(r'', PessoalViewSet, basename='pessoal')

urlpatterns = router.urls
