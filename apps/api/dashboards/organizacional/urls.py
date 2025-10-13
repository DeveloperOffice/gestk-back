from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import OrganizacionalViewSet

router = DefaultRouter()
router.register(r'', OrganizacionalViewSet, basename='organizacional')

urlpatterns = router.urls
