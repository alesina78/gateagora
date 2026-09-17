# -*- coding: utf-8 -*-
"""
Script de DIAGNÓSTICO — não altera nada, só mostra o estado atual.
Rode este primeiro, antes de qualquer correção.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import Empresa, Perfil


def run():
    print("=" * 70)
    print("EMPRESAS CADASTRADAS")
    print("=" * 70)
    for empresa in Empresa.objects.all():
        qtd_funcionarios = empresa.funcionarios.count()
        print(f"  [{empresa.id}] {empresa.nome}  (slug: {empresa.slug})  "
              f"— {qtd_funcionarios} usuário(s) vinculado(s)")

    print()
    print("=" * 70)
    print("TODOS OS USUÁRIOS E SEU NÍVEL DE ACESSO")
    print("=" * 70)
    for user in User.objects.all().order_by('username'):
        try:
            perfil = user.perfil
            empresa_nome = perfil.empresa.nome
            cargo = perfil.cargo
        except Perfil.DoesNotExist:
            empresa_nome = "⚠️  SEM PERFIL — não vê nenhum dado de empresa nenhuma"
            cargo = "—"

        flags = []
        if user.is_superuser:
            flags.append("🔑 SUPERUSER (vê TODAS as empresas)")
        if user.is_staff:
            flags.append("staff (entra no /admin/)")
        if not user.is_active:
            flags.append("❌ INATIVO")

        print(f"  {user.username:20s} | empresa: {empresa_nome:30s} | "
              f"cargo: {cargo:15s} | {', '.join(flags) if flags else '(usuário comum)'}")

    print()
    print("=" * 70)
    print("ALERTAS")
    print("=" * 70)
    sem_perfil = User.objects.filter(perfil__isnull=True, is_superuser=False)
    if sem_perfil.exists():
        print("⚠️  Usuários sem Perfil E sem superuser (não vão ver dado nenhum):")
        for u in sem_perfil:
            print(f"     - {u.username}")

    cargos_validos = {c[0] for c in Perfil.Cargo.choices}
    cargos_invalidos = Perfil.objects.exclude(cargo__in=cargos_validos)
    if cargos_invalidos.exists():
        print("⚠️  Perfis com 'cargo' que não existe nas opções válidas:")
        for p in cargos_invalidos:
            print(f"     - {p.user.username}: cargo='{p.cargo}' (inválido)")

    superusers = User.objects.filter(is_superuser=True)
    print(f"\nTotal de superusers (acesso a TODAS as hípicas): {superusers.count()}")
    for u in superusers:
        print(f"     - {u.username}")


if __name__ == "__main__":
    run()
