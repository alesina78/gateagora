# -*- coding: utf-8 -*-
"""
Redefine a senha SÓ destas três contas: admin, gestor_hipica, gestor_hipica1
Não mexe em mais nenhum usuário.

>>> ANTES DE RODAR: preencha as senhas abaixo, nas variáveis
    NOVA_SENHA_*. Depois de confirmar que funcionou, apague este
    arquivo ou pelo menos limpe as senhas dele -- não deixe
    versionado no Git com senha real dentro.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User

# ── PREENCHA AQUI ANTES DE RODAR ────────────────────────────────────────
NOVA_SENHA_ADMIN = "Dado$Verde"            # <- senha nova para "admin"
NOVA_SENHA_GESTOR_HIPICA = "Dado$Verde"    # <- senha nova para "gestor_hipica"
NOVA_SENHA_GESTOR_HIPICA1 = "Dado$Verde"   # <- senha nova para "gestor_hipica1"
# ─────────────────────────────────────────────────────────────────────


def redefinir(username, nova_senha):
    if not nova_senha:
        print(f"⏭️  {username}: pulado (senha não preenchida no script)")
        return
    try:
        u = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"❌ {username}: usuário não encontrado")
        return
    u.set_password(nova_senha)
    u.is_active = True
    u.save()
    print(f"✅ {username}: senha redefinida, ativo={u.is_active}, "
          f"staff={u.is_staff}, superuser={u.is_superuser}")


def run():
    print("🔑 Redefinindo senhas dos 3 acessos principais...\n")
    redefinir("admin", NOVA_SENHA_ADMIN)
    redefinir("gestor_hipica", NOVA_SENHA_GESTOR_HIPICA)
    redefinir("gestor_hipica1", NOVA_SENHA_GESTOR_HIPICA1)
    print("\n✨ Pronto. Teste o login em /admin/ (para 'admin') "
          "e no dashboard normal (para os dois gestores).")


if __name__ == "__main__":
    run()
