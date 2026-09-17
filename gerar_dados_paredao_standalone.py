# gerar_dados_paredao_standalone.py — Seed standalone (sem manage.py shell)
# Executar com: python gerar_dados_paredao_standalone.py

import os
import django

# Aponta para as suas settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from datetime import date, datetime, timedelta, time
from decimal import Decimal
import random

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction

from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo, Aula,
    ItemEstoque, MovimentacaoFinanceira, DocumentoCavalo, RegistroOcorrencia
)

TZ = timezone.get_current_timezone()
INICIO = date(2025, 11, 1)
FIM = date(2026, 3, 30)
PHONE = "5551991387872"

random.seed(42)

@transaction.atomic
def wipe_data():
    # Ordem por FK
    Aula.objects.all().delete()
    RegistroOcorrencia.objects.all().delete()
    DocumentoCavalo.objects.all().delete()
    MovimentacaoFinanceira.objects.all().delete()
    Cavalo.objects.all().delete()
    Baia.objects.all().delete()
    Piquete.objects.all().delete()
    ItemEstoque.objects.all().delete()
    Aluno.objects.all().delete()
    Perfil.objects.all().delete()
    Empresa.objects.all().delete()

wipe_data()

# Empresa
empresa = Empresa.objects.create(
    nome="Haras do Paredão",
    cidade="Portão/RS",
    cnpj="00.000.000/0000-00",
    slug="haras-do-paredao",
)

# Usuários e Perfis solicitados
su = User.objects.filter(username="Admin").first()
if su:
    Perfil.objects.get_or_create(user=su, defaults=dict(empresa=empresa, cargo=Perfil.Cargo.GESTOR))

admin4, _ = User.objects.get_or_create(username="admin4", defaults=dict(email="gateagora@gmail.com", is_staff=True, is_superuser=False))
if not admin4.has_usable_password():
    admin4.set_password("Gate$2024"); admin4.save()
Perfil.objects.get_or_create(user=admin4, defaults=dict(empresa=empresa, cargo=Perfil.Cargo.GESTOR))

you, _ = User.objects.get_or_create(username="alessandro_admin", defaults=dict(email="alessandro@example.com", is_staff=True))
if not you.has_usable_password():
    you.set_password("Gate2024"); you.save()
Perfil.objects.get_or_create(user=you, defaults=dict(empresa=empresa, cargo=Perfil.Cargo.GESTOR))

gestor, _ = User.objects.get_or_create(username="gestor_hipica1", defaults=dict(email="gestor@paredao.local", is_staff=True))
if not gestor.has_usable_password():
    gestor.set_password("Teste123"); gestor.save()
Perfil.objects.get_or_create(user=gestor, defaults=dict(empresa=empresa, cargo=Perfil.Cargo.GESTOR))

prof_user, _ = User.objects.get_or_create(username="professor_hipica1", defaults=dict(email="prof@paredao.local"))
if not prof_user.has_usable_password():
    prof_user.set_password("Prof123!"); prof_user.save()
prof_perfil, _ = Perfil.objects.get_or_create(user=prof_user, defaults=dict(empresa=empresa, cargo=Perfil.Cargo.PROFESSOR))

# Alunos (15): 5 proprietários humanos + 1 escola + 9 comuns
nomes_proprietarios = [
    "Marina Farias", "Rogério Pacheco", "Cláudia Teles", "Ivan Rocha", "Beatriz Mello"
]
nomes_demais = [
    "Lucas Antunes", "Júlia Freire", "Caio Nunes", "Sofia Martins", "Pedro Reis",
    "Isabela Campos", "André Cardoso", "Carla Silva", "Thiago Alves"
]

aluno_escola = Aluno.objects.create(
    empresa=empresa, nome="Haras do Paredão (Escola)", telefone=PHONE, ativo=True, valor_aula=Decimal("170.00")
)

alunos_proprietarios = [
    Aluno.objects.create(empresa=empresa, nome=n, telefone=PHONE, ativo=True, valor_aula=Decimal("160.00"))
    for n in nomes_proprietarios
]

alunos_demais = [
    Aluno.objects.create(empresa=empresa, nome=n, telefone=PHONE, ativo=True, valor_aula=Decimal("150.00"))
    for n in nomes_demais
]

assert 1 + len(alunos_proprietarios) + len(alunos_demais) == 15

# Estruturas
baias = [Baia.objects.create(empresa=empresa, numero=f"{i:02d}") for i in range(1, 41)]
piquetes = [
    Piquete.objects.create(empresa=empresa, nome="Piquete A", capacidade=8),
    Piquete.objects.create(empresa=empresa, nome="Piquete B", capacidade=10)
]

# Cavalos (32): 17 PROPRIO (Escola) + 15 HOTELARIA (3 por proprietário)
nomes_cavalos = [
    "Trovão", "Estrela", "Ventania", "Flecha", "Hércules", "Aura", "Argos", "Farol",
    "Maestoso", "Jade", "Quiron", "Bravio", "Neblina", "Relâmpago", "Zéfiro", "Apolo",
    "Gaia", "Castor", "Sírius", "Boreal", "Orion", "Pérola", "Safira", "Trueno",
    "Ícaro", "Mistral", "Júpiter", "Naja", "Pégaso", "Capitão", "Talismã", "Xamã"
]
random.shuffle(nomes_cavalos)

cavalos = []

# 17 PROPRIO (14 em baia + 3 em piquete)
next_baia = 0
for idx, nome in enumerate(nomes_cavalos[:17], start=1):
    use_baia = (idx <= 14)
    cav = Cavalo.objects.create(
        empresa=empresa,
        nome=nome,
        categoria="PROPRIO",
        status_saude="Saudável",
        onde_dorme=("BAIA" if use_baia else "PIQUETE"),
        raca=random.choice(["crioulo", "hipismo", "quarto_milha", "mang_marchador"]),
        peso=round(random.uniform(420, 520), 1),
        fator_atividade=random.choice(["0.018", "0.025", "0.035"]),
        tipo_sela="Sela Escola",
        tipo_cabecada="Cabeçada Padrão",
        material_proprio=False,
        baia=(baias[next_baia] if use_baia else None),
        piquete=(None if use_baia else random.choice(piquetes)),
        proprietario=aluno_escola,
        racao_tipo="Guabi Equi-S",
        racao_qtd_manha="2kg",
        racao_qtd_noite="2kg",
        feno_tipo="Coast Cross",
        feno_qtd="À vontade",
        mensalidade_baia=Decimal("0.00")
    )
    if use_baia:
        next_baia += 1
    cavalos.append(cav)

# 15 HOTELARIA: 3 por proprietário (total 5 * 3)
hotel_names = nomes_cavalos[17:]
for i, owner in enumerate(alunos_proprietarios):
    for j in range(3):
        nome = hotel_names[i*3 + j]
        cav = Cavalo.objects.create(
            empresa=empresa,
            nome=nome,
            categoria="HOTELARIA",
            status_saude="Saudável",
            onde_dorme="BAIA",
            raca=random.choice(["crioulo", "hipismo", "quarto_milha", "mang_marchador"]),
            peso=round(random.uniform(430, 530), 1),
            fator_atividade=random.choice(["0.018", "0.025", "0.035"]),
            tipo_sela=("Sela do Proprietário" if (i < 2 and j == 0) else "Sela Escola"),
            tipo_cabecada="Cabeçada Padrão",
            material_proprio=(i < 2 and j == 0),  # 2 com material próprio
            baia=baias[next_baia],
            piquete=None,
            proprietario=owner,
            racao_tipo="Guabi Equi-S",
            racao_qtd_manha="2kg",
            racao_qtd_noite="2kg",
            feno_tipo="Coast Cross",
            feno_qtd="À vontade",
            mensalidade_baia=Decimal("1200.00")
        )
        next_baia += 1
        cavalos.append(cav)

assert len(cavalos) == 32

# Manejo: 2 casqueios (em +3 dias) e 4 vermifugações (em +2 dias)
hoje = timezone.localdate()
casqueio_list = random.sample(cavalos, 2)
restantes = [c for c in cavalos if c not in casqueio_list]
vermi_list = random.sample(restantes, 4)

for c in casqueio_list:
    c.ultimo_casqueamento = hoje - timedelta(days=60)
    c.save(update_fields=["ultimo_casqueamento"])
    RegistroOcorrencia.objects.create(
        cavalo=c,
        titulo="Agendar Casqueamento",
        descricao=f"Casqueamento programado para {(hoje + timedelta(days=3)).strftime('%d/%m/%Y')}",
        data=timezone.make_aware(datetime.combine(hoje + timedelta(days=3), time(9, 0)), TZ),
    )

for c in vermi_list:
    c.ultimo_vermifugo = hoje - timedelta(days=90)
    c.save(update_fields=["ultimo_vermifugo"])
    RegistroOcorrencia.objects.create(
        cavalo=c,
        titulo="Aplicar Vermífugo",
        descricao=f"Vermifugação programada para {(hoje + timedelta(days=2)).strftime('%d/%m/%Y')}",
        data=timezone.make_aware(datetime.combine(hoje + timedelta(days=2), time(10, 30)), TZ),
    )

# Documentos (vacina vencendo)
for c in random.sample(cavalos, 5):
    DocumentoCavalo.objects.create(
        cavalo=c,
        tipo="VACINA",
        titulo="Vacina Influenza",
        data_validade=hoje + timedelta(days=random.randint(5, 30))
    )

# Estoque
ItemEstoque.objects.create(empresa=empresa, nome="Ração Guabi Equi-S", quantidade_atual=4, alerta_minimo=5, unidade="Sacos", fornecedor_contato=PHONE)
ItemEstoque.objects.create(empresa=empresa, nome="Feno Coast Cross", quantidade_atual=12, alerta_minimo=8, unidade="Fardos")
ItemEstoque.objects.create(empresa=empresa, nome="Sal Mineral", quantidade_atual=7, alerta_minimo=6, unidade="Sacos")

# Aulas (01/11/2025 a 30/03/2026, sem domingos, TZ-aware)
dias = []
d = INICIO
while d <= FIM:
    if d.weekday() != 6:  # domingo = 6
        dias.append(d)
    d += timedelta(days=1)

horarios = [time(8,0), time(9,30), time(11,0), time(14,0), time(15,30), time(17,0)]
alunos_para_aula = alunos_demais + alunos_proprietarios[:3]

for d in dias:
    q = random.randint(2, 5)
    usados = set()
    for h in random.sample(horarios, q):
        aluno = random.choice(alunos_para_aula)
        cavalo = random.choice(cavalos)
        key = (d, h, cavalo.id)
        if key in usados:
            continue
        usados.add(key)
        dt_aware = timezone.make_aware(datetime.combine(d, h), TZ)
        Aula.objects.create(
            empresa=empresa,
            aluno=aluno,
            cavalo=cavalo,
            instrutor=prof_perfil,
            data_hora=dt_aware,
            local=random.choice(["picadeiro_1", "picadeiro_2", "pista_salto"]),
            tipo="NORMAL",
            concluida=(d < hoje)
        )

# Financeiro (DateField sem TZ): Nov/2025 .. Mar/2026
meses = [(2025, 11), (2025, 12), (2026, 1), (2026, 2), (2026, 3)]
for (yy, mm) in meses:
    MovimentacaoFinanceira.objects.create(
        empresa=empresa,
        descricao=f"Receita {mm:02d}/{yy}",
        valor=Decimal(str(2500 + random.randint(0, 600))),
        tipo="Receita",
        data=date(yy, mm, 5)
    )
    MovimentacaoFinanceira.objects.create(
        empresa=empresa,
        descricao=f"Despesa {mm:02d}/{yy}",
        valor=Decimal(str(1200 + random.randint(0, 500))),
        tipo="Despesa",
        data=date(yy, mm, 18)
    )

print("Seed concluído para Haras do Paredão (standalone).")
print("Usuários:")
print("- Admin (superuser) — senha Gate$2024, email gateagora@gmail.com")
print("- admin4 (staff) — senha Gate$2024, email gateagora@gmail.com")
print("- alessandro_admin (staff) — senha Gate2024")
print("- gestor_hipica1 (staff) — senha Teste123")
print("- professor_hipica1 — senha Prof123!")