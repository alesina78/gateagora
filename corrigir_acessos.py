# -*- coding: utf-8 -*-
"""
Script de CORREÇÃO de acessos — HPRS (Hípica Paraíso RS)

Corrigido em relação à versão anterior:
1. cargo='Admin' não existia nas opções do Model -> trocado pra um cargo
   válido (Gestor), já que "acesso total" não é definido por cargo.
2. Acesso a TODAS as hípicas agora é feito com is_superuser=True, que é o
   que o admin.py (BaseEmpresaAdmin) realmente verifica -- cargo nunca
   concede acesso entre empresas, só dentro da própria.
3. Superuser não precisa (e geralmente não deve) ter Perfil vinculado a
   uma empresa específica -- isso evitaria confusão futura sobre "de qual
   empresa é esse admin". Deixado sem Perfil de propósito.
4. Adicionado print final com o resumo de quem tem o quê, pra conferir
   antes de sair rodando em produção.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil


def criar_usuario_da_empresa(username, senha, cargo, empresa):
    """Usuário comum, vinculado a UMA empresa específica, vê só o dela."""
    if cargo not in {c[0] for c in Perfil.Cargo.choices}:
        raise ValueError(
            f"Cargo '{cargo}' não existe. Opções válidas: "
            f"{[c[0] for c in Perfil.Cargo.choices]}"
        )

    u, _ = User.objects.get_or_create(username=username)
    u.set_password(senha)
    u.is_staff = True
    u.is_active = True
    u.is_superuser = False  # explícito: este usuário NÃO vê outras empresas
    u.save()

    perfil, criado = Perfil.objects.get_or_create(
        user=u, defaults={'empresa': empresa, 'cargo': cargo}
    )
    if not criado:
        # já existia -- garante que empresa e cargo estão corretos também
        perfil.empresa = empresa
        perfil.cargo = cargo
        perfil.save()

    print(f"✅ {username}: staff, empresa={empresa.nome}, cargo={cargo}")


def criar_super_admin(username, senha):
    """Acesso a TODAS as hípicas -- via is_superuser, não via cargo."""
    u, _ = User.objects.get_or_create(username=username)
    u.set_password(senha)
    u.is_staff = True
    u.is_superuser = True   # <- é isso, e só isso, que dá acesso a tudo
    u.is_active = True
    u.save()
    print(f"✅ {username}: SUPERUSER — acesso a TODAS as hípicas")


def run():
    print("🚀 Corrigindo e atualizando acessos HPRS...\n")

    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    # Usuários da HPRS -- cada um só vê dados da própria hípica
    criar_usuario_da_empresa("Suzana", "Asterix", Perfil.Cargo.GESTOR, hprs)
    criar_usuario_da_empresa("Dado", "Dado$Verde", Perfil.Cargo.PROFESSOR, hprs)
    criar_usuario_da_empresa("Suzana Schuch", "Dado$Verde", Perfil.Cargo.PROFESSOR, hprs)
    criar_usuario_da_empresa("Alessandro", "Dado$Verde", Perfil.Cargo.PROFESSOR, hprs)
    criar_usuario_da_empresa("Luiza Squeff", "Dado$Verde", Perfil.Cargo.PROFESSOR, hprs)

    # Admin geral -- este sim enxerga TODAS as hípicas cadastradas
    criar_super_admin("Admin", "Dado$Verde")

    print("\n✨ Acessos atualizados! Tente logar agora.")
    print("   Lembre-se: mude essas senhas depois de conferir que funcionou --")
    print("   ficaram em texto puro neste script.")


if __name__ == "__main__":
    run()
