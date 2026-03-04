#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
manage.py — launcher de comandos do Django (Django 6.x)

Coloque este arquivo NA RAIZ do projeto (ao lado das pastas 'core' e 'gateagora').
A variável DJANGO_SETTINGS_MODULE aponta para 'core.settings'.
"""

import os
import sys


def main():
    # Aponta para o settings do seu projeto
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Não foi possível importar Django. Verifique se o ambiente virtual está ativo "
            "e se Django está instalado (pip install django)."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()