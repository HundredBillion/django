import os

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": os.environ.get("DJANGO_TEST_POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("DJANGO_TEST_POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("DJANGO_TEST_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DJANGO_TEST_POSTGRES_PORT", "5432"),
    },
    "other": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "postgres",
        "USER": os.environ.get("DJANGO_TEST_POSTGRES_USER", "postgres"),
        "PASSWORD": os.environ.get("DJANGO_TEST_POSTGRES_PASSWORD", ""),
        "HOST": os.environ.get("DJANGO_TEST_POSTGRES_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DJANGO_TEST_POSTGRES_PORT", "5432"),
        "TEST": {"NAME": "test_django_schema_other"},
    },
}

SECRET_KEY = "django_tests_secret_key"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
USE_TZ = False
