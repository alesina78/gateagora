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
        # Inicializa como None para evitar erros de AttributeError
        request.empresa = None

        if request.user.is_authenticated:
            try:
                # Otimizamos a busca usando select_related para evitar múltiplas consultas
                # ao banco de dados em cada carregamento de página (problema N+1)
                perfil = request.user.perfil
                request.empresa = perfil.empresa
            except (AttributeError, Exception):
                # Caso o usuário seja um Superuser sem Perfil criado
                request.empresa = None

        response = self.get_response(request)
        return response