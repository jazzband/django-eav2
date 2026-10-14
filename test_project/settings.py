from __future__ import annotations

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "secret!"  # noqa: S105

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS: list[str] = []


# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Test Project:
    "test_project.apps.TestAppConfig",
    # Our app:
    "eav",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# Database
# https://docs.djangoproject.com/en/3.1/ref/settings/#databases

# SQLite by default. Set ``EAV_TEST_DB`` to ``postgres`` or ``mysql`` to run
# the suite against a real server (see ``docker-compose.yml``).
_DB_ENGINES = {
    # engine, default port, default user (MySQL needs a user that can create
    # the ``test_*`` database):
    "postgres": ("django.db.backends.postgresql", "15432", "eav"),
    "mysql": ("django.db.backends.mysql", "13306", "root"),
}
_DB_NAME = os.environ.get("EAV_TEST_DB", "sqlite")

if _DB_NAME in _DB_ENGINES:
    _engine, _port, _user = _DB_ENGINES[_DB_NAME]
    DATABASES = {
        "default": {
            "ENGINE": _engine,
            "NAME": os.environ.get("EAV_TEST_DB_NAME", "eav"),
            "USER": os.environ.get("EAV_TEST_DB_USER", _user),
            "PASSWORD": os.environ.get("EAV_TEST_DB_PASSWORD", "eav"),
            "HOST": os.environ.get("EAV_TEST_DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("EAV_TEST_DB_PORT", _port),
        },
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        },
    }


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
EAV2_PRIMARY_KEY_FIELD = "django.db.models.AutoField"


# Password validation
# https://docs.djangoproject.com/en/3.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = []


# Internationalization
# https://docs.djangoproject.com/en/3.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.1/howto/static-files/

STATIC_URL = "/static/"
