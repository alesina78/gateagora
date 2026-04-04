# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
import threading

User = get_user_model()
_thread_locals = threading.local()


class EmpresaMiddleware(MiddlewareMixin):

    def process_request(self, request):
        request.empresa = None
        _thread_locals.empresa = None

        if not request.user.is_authenticated:
            return

        if request.user.is_superuser:
            return

        try:
            perfil = request.user.perfil
            empresa = perfil.empresa
            request.empresa = empresa
            _thread_locals.empresa = empresa
        except Exception as e:
            if settings.DEBUG:
                print(f"[EmpresaMiddleware] Usuário sem perfil: {request.user.username} - {e}")
            request.empresa = None
            _thread_locals.empresa = None

    def process_response(self, request, response):
        if hasattr(_thread_locals, 'empresa'):
            delattr(_thread_locals, 'empresa')
        return response