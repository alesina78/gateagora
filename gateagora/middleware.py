# -*- coding: utf-8 -*-
from django.utils.deprecation import MiddlewareMixin

from django.contrib.auth import get_user_model

User = get_user_model()
import threading

# Thread-local storage para maior segurança em ambientes multi-thread
_thread_locals = threading.local()


class EmpresaMiddleware(MiddlewareMixin):
    """
    Middleware para multi-tenant (multi-empresa).
    Injeta request.empresa de forma segura e eficiente.
    """

    def process_request(self, request):
        # Limpa o valor anterior
        request.empresa = None
        
        if not request.user.is_authenticated:
            return

        # Superuser vê tudo (comum em admin)
        if request.user.is_superuser:
            request.empresa = None
            _thread_locals.empresa = None
            return

        # Usuário normal → deve ter perfil e empresa
        try:
            # Usamos select_related para evitar query extra
            if request.user.is_authenticated:
                try:
                    perfil = request.user.perfil
                    request.empresa = perfil.empresa
                except:
                    request.empresa = None
            else:
                request.empresa = None
            empresa = perfil.empresa

            request.empresa = empresa
            _thread_locals.empresa = empresa   # útil para models/managers

        except (AttributeError, User.perfil.RelatedObjectDoesNotExist, Exception) as e:
            # Logar o erro em desenvolvimento
            if settings.DEBUG:
                print(f"[EmpresaMiddleware] Usuário sem perfil ou empresa: {request.user.username} - Erro: {e}")
            
            request.empresa = None
            _thread_locals.empresa = None

    def process_response(self, request, response):
        # Limpeza opcional
        if hasattr(_thread_locals, 'empresa'):
            delattr(_thread_locals, 'empresa')
        return response