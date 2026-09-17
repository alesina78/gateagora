# -*- coding: utf-8 -*-
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil, ConfigPrazoManejo, Baia

def cadastrar_nova_unidade(nome_haras, slug_haras, username_gestor, senha_gestor):
    print(f"🚀 Cadastrando nova unidade: {nome_haras}...")

    # 1. Criar a Nova Empresa
    empresa, created = Empresa.objects.get_or_create(
        slug=slug_haras,
        defaults={'nome': nome_haras, 'cidade': "Definir Cidade"}
    )
    if not created:
        print(f"❌ Erro: O slug '{slug_haras}' já está em uso.")
        return

    # 2. Criar o Usuário do Gestor
    if not User.objects.filter(username=username_gestor).exists():
        user = User.objects.create_user(username=username_gestor, password=senha_gestor)
        print(f"✅ Usuário '{username_gestor}' criado.")
    else:
        print(f"⚠️ Usuário '{username_gestor}' já existe. Vinculando ao perfil...")
        user = User.objects.get(username=username_gestor)

    # 3. Criar o Perfil de Gestor vinculado a ESTA empresa
    Perfil.objects.get_or_create(
        user=user,
        empresa=empresa,
        defaults={'cargo': 'Gestor'}
    )
    print(f"✅ Perfil de Gestor configurado para {nome_haras}.")

    # 4. Configuração de Prazos Padrão
    ConfigPrazoManejo.objects.get_or_create(
        empresa=empresa,
        defaults={
            'prazo_vacina': 365, 'prazo_vermifugo': 90,
            'prazo_ferrageamento': 45, 'prazo_casqueamento': 45
        }
    )
    print(f"✅ Prazos de manejo iniciais configurados.")

    # 5. Criar 5 Baias Iniciais (Opcional, mas ajuda muito)
    for i in range(1, 6):
        Baia.objects.get_or_create(empresa=empresa, numero=str(i))
    print(f"✅ 5 Baias iniciais criadas para {nome_haras}.")

    print(f"\n✨ TUDO PRONTO! O gestor pode logar com '{username_gestor}'.")

if __name__ == "__main__":
    # --- EDITE OS DADOS ABAIXO PARA O NOVO HARAS ---
    cadastrar_nova_unidade(
        nome_haras="Haras Recanto Gaúcho", 
        slug_haras="recanto-gaucho", 
        username_gestor="gestor_recanto", 
        senha_gestor="Gate2026!"
    )