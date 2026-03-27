# -*- coding: utf-8 -*-
from django.contrib.auth.models import User

class EmpresaMiddleware:
    """
    Middleware para injetar a instância da Empresa diretamente no objeto request.
    Isso permite acessar request.empresa em qualquer View ou Template.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Inicializa como None para evitar erros de AttributeError
        request.empresa = None

        # 2. O bloco IF abaixo deve estar EXATAMENTE com 8 espaços de recuo
        if request.user.is_authenticated:
            if request.user.is_superuser:
                # Superuser não é filtrado por empresa (vê tudo no admin)
                request.empresa = None
            else:
                try:
                    # Garantimos que usuários comuns SEMPRE tenham uma empresa vinculada
                    perfil = request.user.perfil
                    request.empresa = perfil.empresa
                except (AttributeError, Exception):
                    request.empresa = None

        response = self.get_response(request)
        return response