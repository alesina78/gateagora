# -*- coding: utf-8 -*-
import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil, Aluno, Piquete, Cavalo

def run():
    print("🚀 Corrigindo e atualizando acessos HPRS...")

    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    def criar_usuario_com_acesso(username, senha, cargo):
        # Busca o usuário ou cria se não existir
        u, created = User.objects.get_or_create(username=username)
        u.set_password(senha)
        u.is_staff = True  # ESSENCIAL: Permite entrar no painel administrativo
        u.is_active = True
        u.save()
        
        # Vincula ao perfil da empresa
        Perfil.objects.get_or_create(user=u, empresa=hprs, defaults={'cargo': cargo})
        print(f"✅ Usuário {username} pronto para logar.")

    # Criando/Atualizando com a regra Dado$Verde
    # Nota: No login, digite EXATAMENTE como está abaixo (respeitando Maiúsculas)
    criar_usuario_com_acesso("Suzana", "Asterix", 'Gestor')
    criar_usuario_com_acesso("Dado", "Dado$Verde", 'Professor')
    criar_usuario_com_acesso("Suzana Schuch", "Dado$Verde", 'Professor')
    criar_usuario_com_acesso("Alessandro", "Dado$Verde", 'Professor')
    criar_usuario_com_acesso("Luiza Squeff", "Dado$Verde", 'Professor')
    
    print("✨ Acessos atualizados! Tente logar agora.")

if __name__ == "__main__":
    run()