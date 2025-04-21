from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "test"
DEBUG = True
ALLOWED_HOSTS = []

INSTALLED_APPS = [
    "django.contrib.contenttypes",
]

MIDDLEWARE = []

ROOT_URLCONF = "consultingmanager.urls"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",  # Use in-memory database
    }
}

TEMPLATES = []

# Completely disable logging
LOGGING_CONFIG = None
import logging
logging.basicConfig(handlers=[logging.NullHandler()]) 