#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
manage.py — Launcher de comandos do Django (Django 6.x)

Uso comum:
    python manage.py runserver
    python manage.py makemigrations
    python manage.py migrate
    python manage.py createsuperuser
    python manage.py collectstatic

Observações importantes:
- Este arquivo deve ficar NA RAIZ do projeto (ao lado de 'core/' e 'gateagora/').
- A variável DJANGO_SETTINGS_MODULE aponta para 'core.settings'.
- Incluímos um pequeno ajuste no sys.path para evitar erros ao mover o projeto de pasta.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _ensure_paths() -> None:
    """
    Garante que o diretório do manage.py (raiz do projeto) esteja no sys.path,
    evitando erros de import quando o projeto é movido de pasta.
    """
    current_dir = Path(__file__).resolve().parent
    if str(current_dir) not in sys.path:
        sys.path.insert(0, str(current_dir))

    # Se quiser subir um nível por algum motivo (monorepo, etc.), ajuste aqui:
    # project_root = current_dir
    # if str(project_root) not in sys.path:
    #     sys.path.insert(0, str(project_root))


def main() -> None:
    """
    Ponto de entrada do utilitário de linha de comando do Django.
    """
    _ensure_paths()

    # Aponta para o settings do seu projeto
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Mensagem de erro mais amigável para ambiente sem Django/venv desativado
        raise ImportError(
            "Não foi possível importar o Django. Verifique se o ambiente virtual está ativo "
            "e se as dependências foram instaladas:\n\n"
            "  1) Ativar venv (Windows PowerShell):\n"
            "     .\\.venv\\Scripts\\Activate.ps1    (ou)    .\\venv\\Scripts\\Activate.ps1\n\n"
            "  2) Instalar dependências:\n"
            "     pip install -r requirements.txt\n"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()