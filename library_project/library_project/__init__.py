# Import Celery to make it work on app startup
from .celery import app as celery_app

__all__ = ('celery_app',)
