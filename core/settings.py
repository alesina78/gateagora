"""
Django settings for core project.
GATE 4 - The best break
"""

from pathlib import Path
import os

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Segurança
SECRET_KEY = 'django-insecure-*+w+fr$4k3r!^l8#7dq$3ikcxq7yrq$1huf@b$7wqhz(9osoay'
DEBUG = True
ALLOWED_HOSTS = []

# Definição das Apps
INSTALLED_APPS = [
    'unfold',  # Deve vir antes do admin para o design funcionar
    'gateagora',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # DIRS configurado para buscar a pasta templates na raiz também
        'DIRS': [BASE_DIR / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media', # Essencial para fotos
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# Banco de Dados
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Validação de Senha
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Regionalização (Brasil)
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# --- ARQUIVOS ESTÁTICOS E DE MÍDIA ---
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Pasta onde você coloca seus arquivos estáticos (CSS, JS, Imagens)
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- CONFIGURAÇÃO DO PAINEL UNFOLD (GATE 4) ---
UNFOLD = {
    "SITE_TITLE": "Gate 4",
    "SITE_HEADER": "Gate 4",
    "SITE_SYMBOL": "🐎",
    "COLORS": {
        "primary": {
            "50": "236, 253, 245",
            "100": "209, 250, 229",
            "200": "167, 243, 208",
            "300": "110, 231, 183",
            "400": "52, 211, 153",
            "500": "16, 185, 129",  # Verde Esmeralda oficial
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
                    {
                        "title": "Monitoramento (Dash)",
                        "icon": "dashboard",
                        "link": "/",  # Abre o dashboard principal
                    },
                ],
            },
            {
                "title": "MANEJO E CADASTROS",
                "items": [
                    {"title": "Cavalos", "icon": "cruelty_free", "link": "/admin/gateagora/cavalo/"},
                    {"title": "Alunos/Sócios", "icon": "person", "link": "/admin/gateagora/aluno/"},
                    {"title": "Estoque", "icon": "inventory_2", "link": "/admin/gateagora/itemestoque/"},
                    {"title": "Aulas", "icon": "calendar_month", "link": "/admin/gateagora/aula/"},
                ],
            },
        ],
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CONFIGURAÇÕES DE REDIRECIONAMENTO DE LOGIN ---
# Resolve o erro 404 em /accounts/profile/
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_URL = '/login/'