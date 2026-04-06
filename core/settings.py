# -*- coding: utf-8 -*-
"""
Django settings — GATE 4
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------------------------
# SEGURANÇA
# ------------------------------------------------------------------------------

SECRET_KEY = os.getenv(
    'DJANGO_SECRET_KEY',
    'django-insecure-*+w+fr$4k3r!^l8#7dq$3ikcxq7yrq$1huf@b$7wqhz(9osoay'
)

DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')

CSRF_TRUSTED_ORIGINS = (
    os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',')
    if os.getenv('DJANGO_CSRF_TRUSTED_ORIGINS')
    else []
)


# ------------------------------------------------------------------------------
# APLICAÇÕES
# ------------------------------------------------------------------------------

INSTALLED_APPS = [
    'unfold',
    'gateagora',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'cloudinary',
    'cloudinary_storage',
]


# ------------------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------------------

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',

    # Autenticação
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    # Multi-Tenant / Multi-Empresa
    'gateagora.middleware.EmpresaMiddleware',

    # Outros
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# ------------------------------------------------------------------------------
# URLs e Templates
# ------------------------------------------------------------------------------

ROOT_URLCONF = 'core.urls'          # ← ESSA LINHA ESTAVA FALTANDO!

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Garanta que o BASE_DIR / 'templates' está aqui
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# ------------------------------------------------------------------------------
# BANCO DE DADOS
# ------------------------------------------------------------------------------

DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# ------------------------------------------------------------------------------
# SENHAS
# ------------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# ------------------------------------------------------------------------------
# LOCALIZAÇÃO
# ------------------------------------------------------------------------------

LANGUAGE_CODE = 'pt-br'
TIME_ZONE     = 'America/Sao_Paulo'
USE_I18N      = True
USE_TZ        = True


# ------------------------------------------------------------------------------
# ARQUIVOS ESTÁTICOS
# ------------------------------------------------------------------------------

STATIC_URL        = '/static/'
STATIC_ROOT       = BASE_DIR / 'staticfiles'
STATICFILES_DIRS  = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# ------------------------------------------------------------------------------
# ARQUIVOS DE MÍDIA
# ------------------------------------------------------------------------------

CLOUDINARY_URL = os.getenv('CLOUDINARY_URL')

if CLOUDINARY_URL:
    import cloudinary
    cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)
    DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# ------------------------------------------------------------------------------
# UNFOLD — Tema do Admin
# ------------------------------------------------------------------------------

UNFOLD = {
    "SITE_TITLE":  "Gate 4",
    "SITE_HEADER": "Gate 4",
    "SITE_SYMBOL": "🐎",
    "COLORS": {
        "primary": {
            "50":  "236, 253, 245",
            "100": "209, 250, 229",
            "200": "167, 243, 208",
            "300": "110, 231, 183",
            "400": "52, 211, 153",
            "500": "16, 185, 129",
            "600": "5, 150, 105",
            "700": "4, 120, 87",
            "800": "6, 95, 70",
            "900": "6, 77, 62",
            "950": "2, 44, 34",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "navigation": [
            {
                "title": "OPERACIONAL",
                "items": [
                    {"title": "Monitoramento (Dash)", "icon": "dashboard", "link": "/"},
                ],
            },
            {
                "title": "MANEJO E CADASTROS",
                "items": [
                    {"title": "Cavalos",       "icon": "cruelty_free",   "link": "/admin/gateagora/cavalo/"},
                    {"title": "Alunos/Sócios", "icon": "person",          "link": "/admin/gateagora/aluno/"},
                    {"title": "Estoque",        "icon": "inventory_2",    "link": "/admin/gateagora/itemestoque/"},
                    {"title": "Aulas",          "icon": "calendar_month", "link": "/admin/gateagora/aula/"},
                    {"title": "Financeiro",     "icon": "payments",       "link": "/admin/gateagora/movimentacaofinanceira/"},
                ],
            },
        ],
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ------------------------------------------------------------------------------
# LOGIN
# ------------------------------------------------------------------------------

LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL           = '/login/'


# ------------------------------------------------------------------------------
# SEGURANÇA EXTRA (Produção)
# ------------------------------------------------------------------------------

if not DEBUG:
    SECURE_PROXY_SSL_HEADER        = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE          = True
    CSRF_COOKIE_SECURE             = True
    SECURE_SSL_REDIRECT            = True
    SECURE_HSTS_SECONDS            = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD            = True
    X_FRAME_OPTIONS                = 'DENY'