from django.apps import AppConfig


class PayAppConfig(AppConfig):
    """Django app configuration for Payment Control System."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pay_app'

    def ready(self) -> None:
        """Register signal handlers when Django app registry is ready."""
        from . import signals