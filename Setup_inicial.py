# -*- coding: utf-8 -*-
import os
import django

# Configura o ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil, ConfigPrazoManejo

def executar_setup():
    print("🚀 Iniciando Setup Inicial do Gate 4...")

    # 1. Criar a Empresa
    empresa, created = Empresa.objects.get_or_create(
        slug="haras-modelo",
        defaults={'nome': "Haras Modelo Principal", 'cidade': "Portão/RS"}
    )
    if created: print(f"✅ Empresa '{empresa.nome}' criada.")
    else: print(f"ℹ️ Empresa '{empresa.nome}' já existe.")

    # 2. Garantir o Superusuário
    username = "admin"
    if not User.objects.filter(username=username).exists():
        user = User.objects.create_superuser(username, 'admin@gate4.com', 'Gate4@2026!')
        print(f"✅ Superusuário '{username}' criado com sucesso.")
    else:
        user = User.objects.get(username=username)
        print(f"ℹ️ Superusuário '{username}' já existe.")

    # 3. Criar o Perfil de Gestor
    perfil, created = Perfil.objects.get_or_create(
        user=user,
        defaults={'empresa': empresa, 'cargo': 'Gestor'}
    )
    if created: print(f"✅ Perfil de Gestor vinculado ao '{username}'.")

    # 4. Criar Configuração de Prazos (Essencial para o Dashboard)
    config, created = ConfigPrazoManejo.objects.get_or_create(
        empresa=empresa,
        defaults={
            'prazo_vacina': 365,
            'prazo_vermifugo': 90,
            'prazo_ferrageamento': 45,
            'prazo_casqueamento': 45
        }
    )
    if created: print(f"✅ Prazos de manejo configurados para a empresa.")

    print("\n✨ Setup concluído! Você já pode logar no sistema.")

if __name__ == "__main__":
    executar_setup()