# -*- coding: utf-8 -*-
"""
SCRIPT DE CARGA TOTAL — Hípica Paraíso RS
Versão CORRIGIDA (bugs B1–B5 resolvidos)

Correções aplicadas:
  B1 — DocumentoCavalo usa data_validade (não data_vencimento)
  B3 — Aula usa data_hora, concluida, instrutor (Perfil) — não data/hora_inicio/status/professor
  B4 — Removido campo 'observacoes' que não existe em Cavalo
  B5 — instrutor recebe Perfil, não User
"""
import os
import django
import random
from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo,
    Aula, ItemEstoque, DocumentoCavalo
)


def run():
    print("🚀 Iniciando Carga TOTAL de Dados: Hípica Paraíso RS...")

    # ── 1. EMPRESA ────────────────────────────────────────────────────────────
    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    # ── 2. EQUIPE ─────────────────────────────────────────────────────────────
    # Retorna o User (para uso posterior ao buscar o Perfil)
    def configurar_equipe(username, senha, cargo):
        u, _ = User.objects.get_or_create(username=username)
        u.set_password(senha)
        u.is_staff = True
        u.is_active = True
        u.save()
        Perfil.objects.update_or_create(
            user=u,
            defaults={'empresa': hprs, 'cargo': cargo}
        )
        return u

    u_suzana    = configurar_equipe("Suzana",       "Asterix",    'Gestor')
    u_dado      = configurar_equipe("Dado",         "Dado$Verde", 'Professor')
    u_ale       = configurar_equipe("Alessandro",   "Dado$Verde", 'Professor')
    u_luiza     = configurar_equipe("Luiza Squeff", "Dado$Verde", 'Professor')
    configurar_equipe("Rodrigo",  "Dado$Verde", 'Tratador')
    configurar_equipe("Maurício", "Dado$Verde", 'Tratador')
    print("✅ Equipe e acessos configurados.")

    # B5 FIX: instrutor precisa ser Perfil, não User
    perfis_professores = list(
        Perfil.objects.filter(empresa=hprs, cargo='Professor')
    )

    # ── 3. ESTRUTURA FÍSICA ───────────────────────────────────────────────────
    piquete_principal, _ = Piquete.objects.get_or_create(
        nome="Piquete Principal", empresa=hprs, defaults={'capacidade': 50}
    )
    for i in range(1, 33):
        Baia.objects.get_or_create(numero=str(i), empresa=hprs)
    print("✅ Estrutura física (32 Baias + Piquete) criada.")

    # ── 4. ALUNOS / PROPRIETÁRIOS ─────────────────────────────────────────────
    nomes_alunos = [
        "Luisa Giordano", "Alice", "Julia", "Julia Charlote", "Joana", "Pietra",
        "Laura", "Marcela", "Juliana Bailarina", "Sofi", "Sandra", "Glênio",
        "Miguel", "Alessandro", "Suzana", "Luiza Squeff", "Carlos Behr",
        "Lisiana", "Liane", "Cecília", "Camila", "Luciana", "Maria Hemília", "Marcelo"
    ]
    alunos_lista = []
    for nome in nomes_alunos:
        al, _ = Aluno.objects.get_or_create(
            nome=nome, empresa=hprs,
            defaults={'telefone': "+5551991387872"}
        )
        alunos_lista.append(al)

    aluno_haras, _ = Aluno.objects.get_or_create(
        nome="Haras Paraíso RS", empresa=hprs,
        defaults={'telefone': "+5551991387872"}
    )
    print("✅ Alunos/Proprietários processados.")

    # ── 5. CAVALOS ────────────────────────────────────────────────────────────
    # Formato: (Nome, Usa_ferradura, Dono, Dorme, Local_piquete)
    # B4 FIX: removido campo 'observacoes' (não existe no model Cavalo)
    cavalos_dados = [
        ("Galileu HPRD",     False, "Haras Paraíso RS", "PIQUETE", "PIQUETE"),
        ("Baruk",            True,  "Cecília",           "BAIA",    "PIQUETE"),
        ("Jade",             True,  "Camila",            "BAIA",    "PIQUETE"),
        ("Soneto",           True,  "Luciana",           "BAIA",    "PIQUETE"),
        ("Zenda",            True,  "Camila",            "BAIA",    "PIQUETE"),
        ("Catita",           True,  "Maria Hemília",     "BAIA",    "PIQUETE"),
        ("Handover",         True,  "Camila",            "BAIA",    "PIQUETE"),
        ("Charlote",         False, "Julia",             "BAIA",    "PIQUETE"),
        ("Pegaus",           True,  "Marcelo",           "BAIA",    "PIQUETE"),
        ("Pé de Pano HPRD",  False, "Haras Paraíso RS", "BAIA",    "PIQUETE"),
        ("Bailarina",        True,  "Julia",             "BAIA",    "BAIA"),
        ("Havaiano",         True,  "Cecília",           "BAIA",    "PIQUETE"),
        ("Gringa",           False, "Marcela",           "BAIA",    "PIQUETE"),
        ("Gatiada HPRD",     False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Fina Flor HPRD",   False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Braína HPRD",      False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Danuza HPRD",      False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Amiga HPRD",       False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Bordada HPRD",     False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Aromah HPRD",      False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Fênix HPRD",       False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Badalada HPRD",    False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Jobin HPRD",       False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Zeus",             False, "Luisa Giordano",   "BAIA",    "BAIA"),
        ("Asterix HPRD",     False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Duque HPRD",       False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Órion HPRD",       False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Trovão HPRD",      False, "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Relâmpago HPRD",   True,  "Haras Paraíso RS", "BAIA",    "BAIA"),
        ("Zorro",            True,  "Alice",             "BAIA",    "BAIA"),
        ("Diamante",         True,  "Joana",             "BAIA",    "BAIA"),
        ("Pérola",           False, "Pietra",            "BAIA",    "BAIA"),
    ]

    cavalos_criados = []
    hoje = timezone.localdate()

    for i, (nome, ferradura, prop_nome, dorme, local) in enumerate(cavalos_dados):
        dono, _ = Aluno.objects.get_or_create(nome=prop_nome, empresa=hprs)

        baia_vinc = None
        if dorme == "BAIA":
            baia_vinc = Baia.objects.filter(empresa=hprs, numero=str(i + 1)).first()

        cav, _ = Cavalo.objects.update_or_create(
            nome=nome, empresa=hprs,
            defaults={
                'categoria':        'PROPRIO' if "HPRD" in nome else 'HOTELARIA',
                'proprietario':     dono,
                'usa_ferradura':    'SIM' if ferradura else 'NAO',
                # B4 FIX: sem campo 'observacoes' — não existe no model
                'onde_dorme':       dorme,
                'baia':             baia_vinc,
                'piquete':          piquete_principal if local == "PIQUETE" else None,
                'status_saude':     'Saudável',
                'ultima_vacina':    hoje - timedelta(days=random.randint(20, 180)),
                'ultimo_vermifugo': hoje - timedelta(days=random.randint(10, 60)),
            }
        )
        cavalos_criados.append(cav)

        # B1 FIX: DocumentoCavalo usa data_validade (não data_vencimento)
        status_doc  = 'VENCIDO' if "Danuza" in nome else 'EM_DIA'
        vencimento  = hoje - timedelta(days=15) if status_doc == 'VENCIDO' else hoje + timedelta(days=90)
        DocumentoCavalo.objects.update_or_create(
            cavalo=cav, tipo='GTA',
            defaults={
                'titulo':        f"GTA — {nome}",
                'data_validade': vencimento,   # campo correto no model
            }
        )

    print(f"✅ {len(cavalos_criados)} cavalos cadastrados e documentos gerados.")

    # ── 6. ESTOQUE CRÍTICO ────────────────────────────────────────────────────
    estoque_itens = [
        ("Feno",           2,  10),
        ("Ração Algibeira", 3, 15),
        ("Serragem",       1,   5),
        ("Alfafa",         2,   8),
    ]
    for nome_item, atual, minimo in estoque_itens:
        ItemEstoque.objects.update_or_create(
            nome=nome_item, empresa=hprs,
            defaults={
                'quantidade_atual': atual,
                'alerta_minimo':    minimo,
                'unidade':          'FARDO',
            }
        )
    print("✅ Estoque crítico configurado.")

    # ── 7. HISTÓRICO DE AULAS ─────────────────────────────────────────────────
    # B1 + B5 FIX: campos corretos (data_hora, concluida, instrutor=Perfil)
    print("⏳ Gerando histórico de aulas (Nov/25 a Abr/26)...")

    if not perfis_professores:
        print("⚠️  Nenhum Perfil de Professor encontrado. Aulas não geradas.")
    else:
        data_ini = date(2025, 11, 1)
        data_fim = date(2026, 4, 30)
        total_dias = (data_fim - data_ini).days
        horas_aula = [9, 14, 16]

        for i in range(total_dias + 1):
            dia = data_ini + timedelta(days=i)
            if dia.weekday() == 6:   # pula domingo
                continue

            for _ in range(2):
                cav    = random.choice(cavalos_criados)
                alu    = random.choice(alunos_lista)
                perfil = random.choice(perfis_professores)   # B5 FIX
                hora   = random.choice(horas_aula)
                dt_hora = timezone.make_aware(
                    timezone.datetime(dia.year, dia.month, dia.day, hora, 0, 0)
                )

                Aula.objects.create(
                    empresa=hprs,
                    cavalo=cav,
                    aluno=alu,
                    instrutor=perfil,       # B5 FIX: Perfil, não User
                    data_hora=dt_hora,      # B1 FIX: campo correto
                    concluida=True,         # B1 FIX: campo correto (não 'status')
                )

        print("✅ Histórico de aulas gerado.")

    print("\n✨ SUCESSO TOTAL: Hípica Paraíso RS populada com dados reais e históricos!")


if __name__ == "__main__":
    run()
