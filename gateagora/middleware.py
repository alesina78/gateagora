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

        # 1. Usuário não autenticado — deixa passar
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return

        # 2. BLOCO DO SUPERUSER (COLOQUE AQUI)
        if request.user.is_superuser:
            try:
                # Tenta pegar a empresa vinculada ao perfil do admin
                empresa = request.user.perfil.empresa
            except Exception:
                # SE O ADMIN NÃO TIVER PERFIL, pega a primeira empresa do banco para não dar erro
                from gateagora.models import Empresa
                empresa = Empresa.objects.first()
            
            request.empresa = empresa
            _thread_locals.empresa = empresa
            return # Encerra aqui para o admin

        # 3. Usuário comum: busca perfil normalmente
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
            del_emp = getattr(_thread_locals, 'empresa', None)
            if del_emp:
                delattr(_thread_locals, 'empresa')
        return response