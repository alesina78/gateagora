# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
import os

urlpatterns = [
    # 1. Favicon direto na raiz
    path('favicon.ico', serve, {
        'document_root': settings.STATIC_ROOT,
        'path': 'img/favicon-32x32.png',   # ou favicon.ico se preferir
    }),
    
    # 2. Painel Administrativo (Unfold)
    path('admin/', admin.site.urls),

    # 3. Encaminha todas as outras rotas para a pasta gateagora
    path('', include('gateagora.urls')),
    
]

# Servir arquivos de mídia e estáticos durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)