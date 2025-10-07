from django.apps import AppConfig


class BillingApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.api.billing'
    verbose_name = 'API de Billing'
