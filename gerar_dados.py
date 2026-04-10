# -*- coding: utf-8 -*-

# ── Forcar UTF-8 no terminal Windows ────────────────────────────────────────
import sys, io
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
# ─────────────────────────────────────────────────────────────────────────────
"""
Seed completo Gate 4 — versão corrigida
Apaga apenas dados de conteúdo (NÃO apaga usuários já existentes)
Recria base fictícia realista
Período: 01/11/2025 → 30/04/2026

Empresas:
  - Haras Elite Prateada   (slug: haras-elite-prateada)
  - Hípica Cavalos do Sul  (slug: hipica-cavalos-sul)

Usuários pré-existentes mantidos:
  AdminGate / DadoManco$29 (superuser)
  Gate4 / Gate2026
  gestor_hipica  / DadoManco$29  → Haras Elite Prateada
  gestor_hipica1 / DadoManco$29  → Hípica Cavalos do Sul
  Suzana / Asterix               → professora, ambas empresas
  Aluno33 / Aluno$2026           → aluno

Execute no shell Django:
  python manage.py shell < gerar_dados.py
"""

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from django.db import connection

# ── Garante UTF-8 na conexão com o banco (crítico no Windows) ────────────────
try:
    with connection.cursor() as cursor:
        cursor.execute("SET client_encoding TO 'UTF8';")
except Exception:
    pass  # SQLite não precisa, Postgres sim
# ────────────────────────────────────────────────────────────────────────────

from gateagora.models import (
    Aluno, Aula, Baia, Cavalo, ConfigPrazoManejo,
    DocumentoCavalo, Empresa, Fatura, ItemEstoque,
    ItemFatura, MovimentacaoFinanceira, Perfil,
    Piquete, RegistroOcorrencia,
)

random.seed(42)

TELEFONE = "5551991387872"
INICIO   = date(2025, 11, 1)
FIM      = date(2026, 4, 30)
HOJE     = timezone.localdate()

# ─────────────────────────────────────────────
# 1. LIMPEZA DE CONTEÚDO (não apaga usuários)
# ─────────────────────────────────────────────
print("🧹 Limpando dados de conteúdo...")

Aula.objects.all().delete()
ItemFatura.objects.all().delete()
Fatura.objects.all().delete()
DocumentoCavalo.objects.all().delete()
RegistroOcorrencia.objects.all().delete()
MovimentacaoFinanceira.objects.all().delete()
ItemEstoque.objects.all().delete()
Cavalo.objects.all().delete()
Baia.objects.all().delete()
Piquete.objects.all().delete()
Aluno.objects.all().delete()
ConfigPrazoManejo.objects.all().delete()
Empresa.objects.all().delete()
# Perfis vinculados às empresas deletadas serão removidos em cascata
Perfil.objects.all().delete()

# ─────────────────────────────────────────────
# 2. EMPRESAS
# ─────────────────────────────────────────────
print("🏢 Criando empresas...")

emp1 = Empresa.objects.create(
    nome="Haras Elite Prateada",
    slug="haras-elite-prateada",
    cidade="Porto Alegre",
)
emp2 = Empresa.objects.create(
    nome="Hípica Cavalos do Sul",
    slug="hipica-cavalos-sul",
    cidade="Caxias do Sul",
)

# ─────────────────────────────────────────────
# 3. PRAZOS DE MANEJO
# ─────────────────────────────────────────────
for emp in [emp1, emp2]:
    ConfigPrazoManejo.objects.create(
        empresa=emp,
        prazo_vacina=180,
        prazo_vermifugo=90,
        prazo_ferrageamento=45,
        prazo_casqueamento=30,
    )

# ─────────────────────────────────────────────
# 4. USUÁRIOS (preserva existentes, recria perfis)
# ─────────────────────────────────────────────
print("👤 Configurando usuários...")

def get_or_create_user(username, senha, is_superuser=False, is_staff=True):
    u, criado = User.objects.get_or_create(username=username)
    if criado or not u.password:
        u.set_password(senha)
    u.is_superuser = is_superuser
    u.is_staff     = is_staff
    u.is_active    = True
    u.save()
    return u

def criar_perfil(user, empresa, cargo):
    Perfil.objects.filter(user=user).delete()
    return Perfil.objects.create(
        user=user,
        empresa=empresa,
        cargo=cargo,
        telefone=TELEFONE,
    )

# Superuser
u_admin = get_or_create_user("AdminGate", "DadoManco$29", is_superuser=True)

# Usuário sem empresa (acesso geral)
u_gate4 = get_or_create_user("Gate4", "Gate2026")

# Gestores
u_gestor1 = get_or_create_user("gestor_hipica",  "DadoManco$29")
u_gestor2 = get_or_create_user("gestor_hipica1", "DadoManco$29")
criar_perfil(u_gestor1, emp1, "Gestor")
criar_perfil(u_gestor2, emp2, "Gestor")

# Professores — Suzana e Alessandro vinculados à emp1
u_suzana    = get_or_create_user("Suzana",        "Asterix")
u_alessand  = get_or_create_user("Alessandro",    "Gate2026")
u_luiza_sq  = get_or_create_user("LuizaSqueff",   "Gate2026")
p_suz1  = criar_perfil(u_suzana,   emp1, "Professor")
p_ale1  = criar_perfil(u_alessand, emp1, "Professor")
p_lui1  = criar_perfil(u_luiza_sq, emp1, "Professor")

# Tratadores
u_rodrigo = get_or_create_user("Rodrigo",  "Gate2026")
u_mauricio = get_or_create_user("Mauricio", "Gate2026")
criar_perfil(u_rodrigo,  emp1, "Tratador")
criar_perfil(u_mauricio, emp1, "Tratador")

# Aluno padrão
u_aluno33 = get_or_create_user("Aluno33", "Aluno$2026")

print("✅ Usuários configurados.")

# ─────────────────────────────────────────────────────────────────────────────
# 5. HELPER
# ─────────────────────────────────────────────────────────────────────────────

def criar_baias(empresa, quantidade):
    baias = []
    for i in range(1, quantidade + 1):
        baias.append(Baia.objects.create(
            empresa=empresa,
            numero=str(i),
            status="Livre",
        ))
    return baias

def criar_piquetes(empresa, nomes):
    piquetes = []
    for nome in nomes:
        piquetes.append(Piquete.objects.create(
            empresa=empresa,
            nome=nome,
            capacidade=6,
            status="Livre",
        ))
    return piquetes

def doc_em_dia(cavalo, tipo, titulo, anos_atras=0, meses_atras=0, validade_dias=365):
    """Cria DocumentoCavalo com data já passada e validade futura."""
    base = HOJE - timedelta(days=int(anos_atras * 365 + meses_atras * 30))
    return DocumentoCavalo.objects.create(
        cavalo=cavalo,
        tipo=tipo,
        titulo=titulo,
        data_validade=base + timedelta(days=validade_dias),
    )

def vacinas_em_dia(cavalo, meses_atras=2):
    """Cria vacina + exame + GTA todos em dia."""
    doc_em_dia(cavalo, "VACINA", "Atestado de Vacinação", meses_atras=meses_atras, validade_dias=150)
    doc_em_dia(cavalo, "EXAME",  "Exame Mormo/Anemia",    meses_atras=meses_atras, validade_dias=150)
    doc_em_dia(cavalo, "GTA",    "GTA Vigente",            meses_atras=meses_atras, validade_dias=150)

def set_manejo_em_dia(cavalo, usa_ferradura="NAO", dias_atras_vacina=30,
                      dias_atras_verm=20, dias_atras_casco=10, dias_atras_ferr=10):
    cavalo.ultima_vacina    = HOJE - timedelta(days=dias_atras_vacina)
    cavalo.ultimo_vermifugo = HOJE - timedelta(days=dias_atras_verm)
    if usa_ferradura == "SIM":
        cavalo.ultimo_ferrageamento = HOJE - timedelta(days=dias_atras_ferr)
        cavalo.ultimo_casqueamento  = None   # ← zera o campo oposto
    else:
        cavalo.ultimo_casqueamento  = HOJE - timedelta(days=dias_atras_casco)
        cavalo.ultimo_ferrageamento = None   # ← zera o campo oposto
    cavalo.usa_ferradura = usa_ferradura
    cavalo.save()

# ─────────────────────────────────────────────────────────────────────────────
# 6. EMPRESA 1 — Haras Elite Prateada
# ─────────────────────────────────────────────────────────────────────────────
print("🐎 Populando Haras Elite Prateada...")

baias1    = criar_baias(emp1, 28)
piquetes1 = criar_piquetes(emp1, ["Piquete A", "Piquete B", "Piquete C", "Piquete D"])

# ── Alunos / Proprietários ──────────────────────────────────────────────────

# Aluno institucional (dono dos cavalos HPRD)
haras1 = Aluno.objects.create(empresa=emp1, nome="Haras Paraíso RS", telefone=TELEFONE)

# Proprietários particulares
cecilia  = Aluno.objects.create(empresa=emp1, nome="Cecília Fontana",    telefone=TELEFONE)
camila   = Aluno.objects.create(empresa=emp1, nome="Camila Ferreira",    telefone=TELEFONE)
luciana  = Aluno.objects.create(empresa=emp1, nome="Luciana Prado",      telefone=TELEFONE)
maria_h  = Aluno.objects.create(empresa=emp1, nome="Maria Hemília Costa",telefone=TELEFONE)
julia    = Aluno.objects.create(empresa=emp1, nome="Júlia Mendonça",     telefone=TELEFONE)
marcelo  = Aluno.objects.create(empresa=emp1, nome="Marcelo Ribeiro",    telefone=TELEFONE)
marcela  = Aluno.objects.create(empresa=emp1, nome="Marcela Dutra",      telefone=TELEFONE)
luisa_g  = Aluno.objects.create(empresa=emp1, nome="Luísa Giordano",     telefone=TELEFONE)

# Alunos sem cavalo próprio
alice    = Aluno.objects.create(empresa=emp1, nome="Alice Borges",       telefone=TELEFONE)
joana    = Aluno.objects.create(empresa=emp1, nome="Joana Farias",       telefone=TELEFONE)
pietra   = Aluno.objects.create(empresa=emp1, nome="Pietra Viana",       telefone=TELEFONE)
laura    = Aluno.objects.create(empresa=emp1, nome="Laura Krause",       telefone=TELEFONE)
julia_c  = Aluno.objects.create(empresa=emp1, nome="Júlia Charlote",     telefone=TELEFONE)
juliana_b= Aluno.objects.create(empresa=emp1, nome="Juliana Bailarina",  telefone=TELEFONE)
sofi     = Aluno.objects.create(empresa=emp1, nome="Sofi Alvarez",       telefone=TELEFONE)
sandra   = Aluno.objects.create(empresa=emp1, nome="Sandra Mello",       telefone=TELEFONE)
glenio   = Aluno.objects.create(empresa=emp1, nome="Glênio Trevisan",    telefone=TELEFONE)
miguel   = Aluno.objects.create(empresa=emp1, nome="Miguel Carvalho",    telefone=TELEFONE)
carlos_b = Aluno.objects.create(empresa=emp1, nome="Carlos Behr",        telefone=TELEFONE)
lisiana  = Aluno.objects.create(empresa=emp1, nome="Lisiana Moura",      telefone=TELEFONE)
liane    = Aluno.objects.create(empresa=emp1, nome="Liane Souza",        telefone=TELEFONE)

alunos_aula1 = [alice, joana, pietra, laura, julia_c, juliana_b, sofi,
                sandra, glenio, miguel, carlos_b, lisiana, liane, luisa_g, marcela]

# Vincula Aluno33 como aluno da emp1
criar_perfil(u_aluno33, emp1, "Aluno")

# ── Cavalos — lista detalhada ────────────────────────────────────────────────
# Cavalos HPRD (do haras) — proprietário = haras1, categoria PROPRIO

def cav(empresa, nome, prop, cat, usa_ferr, status, onde_dorme, baia_obj=None,
        piquete_obj=None, mat_proprio=False, raca="srd", peso=480,
        atividade="0.018", sela="", cabecada=""):
    return Cavalo.objects.create(
        empresa=empresa,
        nome=nome,
        proprietario=prop,
        categoria=cat,
        usa_ferradura=usa_ferr,
        status_saude=status,
        onde_dorme=onde_dorme,
        baia=baia_obj,
        piquete=piquete_obj,
        material_proprio=mat_proprio,
        raca=raca,
        peso=peso,
        fator_atividade=atividade,
        tipo_sela=sela,
        tipo_cabecada=cabecada,
        mensalidade_baia=Decimal("1200.00") if cat == "HOTELARIA" else Decimal("0.00"),
    )

# ── HOTELARIA — cavalos particulares (15) ────────────────────────────────────

galileu = cav(emp1, "Galileu HPRD", haras1, "HOTELARIA", "NAO", "Doente",
              "PIQUETE", piquete_obj=piquetes1[0])
# Dores na pata — não treina
RegistroOcorrencia.objects.create(
    cavalo=galileu, titulo="Dores membro anterior esquerdo",
    descricao="Claudicação grau 2. Repouso absoluto indicado. Acompanhamento veterinário.",
    veterinario="Dr. Felipe Marques",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=5), time(9, 0))),
)

baruk = cav(emp1, "Baruk", cecilia, "HOTELARIA", "SIM", "Alerta",
            "BAIA", baia_obj=baias1[0], mat_proprio=True)
RegistroOcorrencia.objects.create(
    cavalo=baruk, titulo="Baixo peso corporal",
    descricao="Escore corporal 3/9. Ajuste de dieta iniciado. Monitorar evolução semanal.",
    veterinario="Dr. Felipe Marques",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=3), time(10, 0))),
)

jade = cav(emp1, "Jade", camila, "HOTELARIA", "SIM", "Saudável",
           "BAIA", baia_obj=baias1[1], mat_proprio=True, peso=520, atividade="0.025")

soneto = cav(emp1, "Soneto", luciana, "HOTELARIA", "SIM", "Tratamento",
             "BAIA", baia_obj=baias1[2], mat_proprio=True)
RegistroOcorrencia.objects.create(
    cavalo=soneto, titulo="Pós-operatório — cólica cirúrgica",
    descricao="Cirurgia realizada em 15/03/2026. Recuperação em andamento. Dieta líquida.",
    veterinario="Dra. Ana Beatriz Lima",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=20), time(8, 0))),
)

zenda = cav(emp1, "Zenda", camila, "HOTELARIA", "SIM", "Doente",
            "BAIA", baia_obj=baias1[3], mat_proprio=True)
RegistroOcorrencia.objects.create(
    cavalo=zenda, titulo="Dores na paleta — tendinite",
    descricao="Inflamação confirmada por ultrassom. Fisioterapia 3x/semana.",
    veterinario="Dr. Felipe Marques",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=8), time(9, 30))),
)

catita = cav(emp1, "Catita", maria_h, "HOTELARIA", "SIM", "Saudável",
             "BAIA", baia_obj=baias1[4], mat_proprio=True, peso=440)

handover = cav(emp1, "Handover", camila, "HOTELARIA", "SIM", "Alerta",
               "BAIA", baia_obj=baias1[5], mat_proprio=True)
RegistroOcorrencia.objects.create(
    cavalo=handover, titulo="Claudicação + aerofagia",
    descricao="Manca membro posterior direito. Aerofágico crônico. Collar anti-aerofagia instalado.",
    veterinario="Dra. Ana Beatriz Lima",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=12), time(14, 0))),
)

charlote = cav(emp1, "Charlote", julia, "HOTELARIA", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[6], mat_proprio=True, peso=460, atividade="0.025")

pegaus = cav(emp1, "Pegaus", marcelo, "HOTELARIA", "SIM", "Saudável",
             "BAIA", baia_obj=baias1[7], mat_proprio=True, peso=500)

pe_de_pano = cav(emp1, "Pé de Pano HPRD", haras1, "HOTELARIA", "NAO", "Alerta",
                 "BAIA", baia_obj=baias1[8])
RegistroOcorrencia.objects.create(
    cavalo=pe_de_pano, titulo="Baixa visão bilateral",
    descricao="Avaliação oftalmológica: catarata senil bilateral grau moderado.",
    veterinario="Dr. Felipe Marques",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=30), time(11, 0))),
)

bailarina = cav(emp1, "Bailarina", julia, "HOTELARIA", "SIM", "Saudável",
                "BAIA", baia_obj=baias1[9], mat_proprio=True, peso=470, atividade="0.025")

havaiano = cav(emp1, "Havaiano", cecilia, "HOTELARIA", "SIM", "Alerta",
               "BAIA", baia_obj=baias1[10], mat_proprio=True)
RegistroOcorrencia.objects.create(
    cavalo=havaiano, titulo="Baixo peso — emagrecimento",
    descricao="Escore 3/9. Investigação parasitária solicitada. Suplementação iniciada.",
    veterinario="Dra. Ana Beatriz Lima",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=7), time(9, 0))),
)

gringa = cav(emp1, "Gringa", marcela, "HOTELARIA", "NAO", "Saudável",
             "BAIA", baia_obj=baias1[11], atividade="0.025")

zeus = cav(emp1, "Zeus", luisa_g, "HOTELARIA", "NAO", "Saudável",
           "BAIA", baia_obj=baias1[12], atividade="0.025")

gatiada = cav(emp1, "Gatiada HPRD", haras1, "HOTELARIA", "NAO", "Alerta",
              "BAIA", baia_obj=baias1[13])
RegistroOcorrencia.objects.create(
    cavalo=gatiada, titulo="Senil — baixa visão e mobilidade reduzida",
    descricao="36 anos. Cuidados paliativos. Pastagem restrita. Não apta para montaria.",
    veterinario="Dr. Felipe Marques",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=60), time(10, 0))),
)

# ── PRÓPRIO — cavalos da escola (17) ─────────────────────────────────────────

fina_flor = cav(emp1, "Fina Flor HPRD", haras1, "PROPRIO", "NAO", "Saudável",
                "BAIA", baia_obj=baias1[14], atividade="0.025")
braina    = cav(emp1, "Braína HPRD",    haras1, "PROPRIO", "NAO", "Saudável",
                "BAIA", baia_obj=baias1[15], atividade="0.025")

danuza = cav(emp1, "Danuza HPRD", haras1, "PROPRIO", "NAO", "Alerta",
             "BAIA", baia_obj=baias1[16])
# Vacina e GTA vencidos
danuza.ultima_vacina    = HOJE - timedelta(days=200)  # prazo 180d → vencida
danuza.ultimo_vermifugo = HOJE - timedelta(days=100)  # vencida
danuza.ultimo_casqueamento = HOJE - timedelta(days=40) # vencida (prazo 30d)
danuza.save()
DocumentoCavalo.objects.create(
    cavalo=danuza, tipo="VACINA", titulo="Atestado de Vacinação",
    data_validade=HOJE - timedelta(days=15),  # VENCIDO
)
DocumentoCavalo.objects.create(
    cavalo=danuza, tipo="GTA", titulo="GTA",
    data_validade=HOJE - timedelta(days=5),   # VENCIDO
)

amiga   = cav(emp1, "Amiga HPRD",    haras1, "PROPRIO", "NAO", "Alerta",
              "BAIA", baia_obj=baias1[17])
RegistroOcorrencia.objects.create(
    cavalo=amiga, titulo="Observação respiratória",
    descricao="Chiado leve durante esforço. Aguardando resultado de exame endoscópico.",
    veterinario="Dra. Ana Beatriz Lima",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=4), time(10, 30))),
)

bordada  = cav(emp1, "Bordada HPRD",  haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[18], atividade="0.025")
aromah   = cav(emp1, "Aromah HPRD",   haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[19], atividade="0.025")
fenix    = cav(emp1, "Fênix HPRD",    haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[20])
badalada = cav(emp1, "Badalada HPRD", haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[21], atividade="0.025")
jobin    = cav(emp1, "Jobin HPRD",    haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[22], atividade="0.025")
asterix  = cav(emp1, "Asterix HPRD",  haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[23], atividade="0.025")
duque    = cav(emp1, "Duque HPRD",    haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[24], atividade="0.025")
orion    = cav(emp1, "Órion HPRD",    haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[25], atividade="0.025")
trovao   = cav(emp1, "Trovão HPRD",   haras1, "PROPRIO", "NAO", "Saudável",
               "BAIA", baia_obj=baias1[26], atividade="0.025")
raio     = cav(emp1, "Raio HPRD",     haras1, "PROPRIO", "SIM", "Saudável",
               "BAIA", baia_obj=baias1[27], atividade="0.025")

# ── Manejo dos cavalos — datas ───────────────────────────────────────────────

# Galileu — nunca teve manejo (novo) → vai aparecer em alerta
galileu.ultima_vacina    = None
galileu.ultimo_vermifugo = None
galileu.ultimo_casqueamento = None
galileu.save()

# Baruk — tudo em dia
set_manejo_em_dia(baruk, "SIM",  dias_atras_vacina=40, dias_atras_verm=30, dias_atras_ferr=15)
# Jade — tudo em dia
set_manejo_em_dia(jade,    "SIM", dias_atras_vacina=35, dias_atras_verm=25, dias_atras_ferr=10)
# Soneto — tudo em dia
set_manejo_em_dia(soneto,  "SIM", dias_atras_vacina=60, dias_atras_verm=45, dias_atras_ferr=20)
# Zenda — tudo em dia
set_manejo_em_dia(zenda,   "SIM", dias_atras_vacina=50, dias_atras_verm=40, dias_atras_ferr=18)
# Catita — tudo em dia
set_manejo_em_dia(catita,  "SIM", dias_atras_vacina=30, dias_atras_verm=20, dias_atras_ferr=12)
# Handover — tudo em dia
set_manejo_em_dia(handover,"SIM", dias_atras_vacina=45, dias_atras_verm=35, dias_atras_ferr=16)
# Charlote — tudo em dia
set_manejo_em_dia(charlote,"NAO", dias_atras_vacina=20, dias_atras_verm=15, dias_atras_casco=8)
# Pegaus — tudo em dia
set_manejo_em_dia(pegaus,  "SIM", dias_atras_vacina=25, dias_atras_verm=18, dias_atras_ferr=14)
# Pé de Pano — tudo em dia
set_manejo_em_dia(pe_de_pano,"NAO",dias_atras_vacina=30,dias_atras_verm=20, dias_atras_casco=12)
# Bailarina — tudo em dia
set_manejo_em_dia(bailarina,"SIM",dias_atras_vacina=22,dias_atras_verm=17, dias_atras_ferr=11)
# Havaiano — tudo em dia
set_manejo_em_dia(havaiano, "SIM",dias_atras_vacina=38,dias_atras_verm=28, dias_atras_ferr=13)
# Gringa — tudo em dia
set_manejo_em_dia(gringa,  "NAO", dias_atras_vacina=15, dias_atras_verm=10, dias_atras_casco=5)
# Zeus — tudo em dia
set_manejo_em_dia(zeus,    "NAO", dias_atras_vacina=28, dias_atras_verm=22, dias_atras_casco=9)
# Gatiada — tudo em dia
set_manejo_em_dia(gatiada, "NAO", dias_atras_vacina=40, dias_atras_verm=30, dias_atras_casco=14)

# Cavalos PRÓPRIOS com manejo em dia
for c, ferr, vac, verm, casco, ferr_d in [
    (fina_flor,  "NAO", 25, 15, 8,  0),
    (braina,     "NAO", 32, 22, 10, 0),
    (bordada,    "NAO", 18, 12, 6,  0),
    (aromah,     "NAO", 20, 14, 7,  0),
    (badalada,   "NAO", 27, 20, 11, 0),
    (jobin,      "NAO", 16, 11, 5,  0),
    (asterix,    "NAO", 30, 21, 12, 0),
    (duque,      "NAO", 35, 25, 13, 0),
    (orion,      "NAO", 29, 19, 9,  0),
    (trovao,     "NAO", 22, 16, 8,  0),
    (raio,       "SIM", 24, 18, 0,  15),
    (fenix,      "NAO", 40, 30, 14, 0),
]:
    set_manejo_em_dia(c, ferr, dias_atras_vacina=vac, dias_atras_verm=verm,
                      dias_atras_casco=casco, dias_atras_ferr=ferr_d)

# ── 4 cavalos com casqueamento próximo (≤ 3 dias do vencimento, prazo=30d) ──
# Prazo casqueamento = 30 dias → último feito há 28d = vence em 2 dias
for c in [charlote, gringa, pe_de_pano, aromah]:
    c.ultimo_casqueamento = HOJE - timedelta(days=28)
    c.save()

# ── 4 cavalos com vermifugação próxima (≤ 2 dias do vencimento, prazo=90d) ──
# Prazo vermifugo = 90 dias → último feito há 89d = vence em 1 dia
for c in [jade, catita, bordada, jobin]:
    c.ultimo_vermifugo = HOJE - timedelta(days=89)
    c.save()

# ── Documentos ───────────────────────────────────────────────────────────────

# Todos em dia (exceto Danuza — já criado acima)
cavalos_em_dia_docs = [
    baruk, jade, soneto, zenda, catita, handover, charlote, pegaus, pe_de_pano,
    bailarina, havaiano, gringa, zeus, gatiada, fina_flor, braina, amiga,
    bordada, aromah, fenix, badalada, jobin, asterix, duque, orion, trovao, raio,
]
for c in cavalos_em_dia_docs:
    vacinas_em_dia(c, meses_atras=2)

# Galileu — nunca vacinado, sem documentos (aparece em alerta total)

# 3 documentos próximos a vencer (dentro de 60 dias)
DocumentoCavalo.objects.create(
    cavalo=baruk, tipo="GTA", titulo="GTA — renovação",
    data_validade=HOJE + timedelta(days=12),
)
DocumentoCavalo.objects.create(
    cavalo=havaiano, tipo="EXAME", titulo="Exame Mormo/Anemia — renovação",
    data_validade=HOJE + timedelta(days=25),
)
DocumentoCavalo.objects.create(
    cavalo=soneto, tipo="GTA", titulo="GTA pós-cirurgia",
    data_validade=HOJE + timedelta(days=35),
)

# ── Estoque ──────────────────────────────────────────────────────────────────

estoque1 = [
    # Críticos (quantidade ≤ alerta_minimo)
    ItemEstoque.objects.create(empresa=emp1, nome="Vermífugo Equalan",    quantidade_atual=2,  alerta_minimo=10, unidade="Doses",  consumo_diario=Decimal("0.5"),  fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp1, nome="Ferraduras Dianteiras",quantidade_atual=4,  alerta_minimo=20, unidade="Pares",  consumo_diario=Decimal("0.8"),  fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp1, nome="Seringas Descartáveis",quantidade_atual=8,  alerta_minimo=50, unidade="Unid",   consumo_diario=Decimal("2.0"),  fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp1, nome="Vacina Influenza",     quantidade_atual=3,  alerta_minimo=15, unidade="Doses",  consumo_diario=Decimal("0.3"),  fornecedor_contato="5551991387872"),
    # Atenção
    ItemEstoque.objects.create(empresa=emp1, nome="Ração Premium 25kg",  quantidade_atual=22, alerta_minimo=15, unidade="Sacos",  consumo_diario=Decimal("1.5"),  fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp1, nome="Feno Coast Cross",     quantidade_atual=18, alerta_minimo=10, unidade="Fardos", consumo_diario=Decimal("1.0"),  fornecedor_contato="5551991387872"),
    # Normais
    ItemEstoque.objects.create(empresa=emp1, nome="Sal Mineral",          quantidade_atual=40, alerta_minimo=10, unidade="KG",     consumo_diario=Decimal("0.8")),
    ItemEstoque.objects.create(empresa=emp1, nome="Shampoo Equino",       quantidade_atual=12, alerta_minimo=4,  unidade="Frascos",consumo_diario=Decimal("0.2")),
    ItemEstoque.objects.create(empresa=emp1, nome="Óleo de Milho",        quantidade_atual=8,  alerta_minimo=3,  unidade="Litros", consumo_diario=Decimal("0.3")),
    ItemEstoque.objects.create(empresa=emp1, nome="Curativo Spray",       quantidade_atual=6,  alerta_minimo=2,  unidade="Frascos"),
]

# ── Aulas / Treinos ──────────────────────────────────────────────────────────

# Cavalos aptos para aula (excluindo os parados por questão de saúde)
cavalos_aula1 = [
    jade, catita, charlote, pegaus, bailarina, gringa, zeus,
    fina_flor, braina, bordada, aromah, badalada, jobin,
    asterix, duque, orion, trovao, raio, havaiano,
]

instrutores1 = [p_suz1, p_ale1, p_lui1]
locais = ["picadeiro_1", "picadeiro_2", "pista_salto"]

print("📅 Gerando aulas Haras Elite Prateada...")
d = INICIO
while d <= FIM:
    if d.weekday() != 6:  # sem domingo
        n_aulas = random.randint(4, 8)
        horarios_usados = set()
        for _ in range(n_aulas):
            hora = random.choice([7, 8, 9, 10, 14, 15, 16, 17])
            if hora in horarios_usados:
                continue
            horarios_usados.add(hora)
            aluno = random.choice(alunos_aula1)
            cavalo = random.choice(cavalos_aula1)
            # Só cria se cavalo e aluno são da mesma empresa
            Aula.objects.create(
                empresa=emp1,
                aluno=aluno,
                cavalo=cavalo,
                instrutor=random.choice(instrutores1),
                tipo=random.choice(["NORMAL", "NORMAL", "RECUPERAR"]),
                data_hora=timezone.make_aware(datetime.combine(d, time(hora, 0))),
                local=random.choice(locais),
                concluida=(d < HOJE),
            )
    d += timedelta(days=1)

# ── Financeiro ───────────────────────────────────────────────────────────────

print("💰 Gerando financeiro Haras Elite Prateada...")
meses_vistos = set()
m = INICIO
while m <= FIM:
    chave = (m.year, m.month)
    if chave not in meses_vistos:
        meses_vistos.add(chave)
        MovimentacaoFinanceira.objects.create(
            empresa=emp1,
            data=date(m.year, m.month, 5),
            tipo="Receita",
            descricao="Mensalidades de hotelaria",
            valor=Decimal(random.randint(14000, 18000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp1,
            data=date(m.year, m.month, 5),
            tipo="Receita",
            descricao="Aulas e treinos",
            valor=Decimal(random.randint(4000, 7000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp1,
            data=date(m.year, m.month, 10),
            tipo="Despesa",
            descricao="Ração e insumos",
            valor=Decimal(random.randint(5000, 8000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp1,
            data=date(m.year, m.month, 15),
            tipo="Despesa",
            descricao="Veterinário e medicamentos",
            valor=Decimal(random.randint(1500, 3500)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp1,
            data=date(m.year, m.month, 20),
            tipo="Despesa",
            descricao="Salários e encargos",
            valor=Decimal(random.randint(6000, 9000)),
        )
    m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)

print("✅ Haras Elite Prateada populado.")

# ─────────────────────────────────────────────────────────────────────────────
# 7. EMPRESA 2 — Hípica Cavalos do Sul
# ─────────────────────────────────────────────────────────────────────────────
print("🐎 Populando Hípica Cavalos do Sul...")

baias2    = criar_baias(emp2, 28)
piquetes2 = criar_piquetes(emp2, ["Piquete Norte", "Piquete Sul", "Piquete Leste"])

# Usuários professores empresa 2
u_suz2 = get_or_create_user("Suzana2", "Asterix")
u_ale2 = get_or_create_user("Alessandro2", "Gate2026")
p_suz2 = criar_perfil(u_suz2, emp2, "Professor")
p_ale2 = criar_perfil(u_ale2, emp2, "Professor")

instrutores2 = [p_suz2, p_ale2]

# Aluno institucional
hipica2 = Aluno.objects.create(empresa=emp2, nome="Hípica Cavalos do Sul", telefone=TELEFONE)

# Proprietários
ana_p   = Aluno.objects.create(empresa=emp2, nome="Ana Paula Meirelles",  telefone=TELEFONE)
roberto = Aluno.objects.create(empresa=emp2, nome="Roberto Figueiredo",   telefone=TELEFONE)
cintia  = Aluno.objects.create(empresa=emp2, nome="Cíntia Hartmann",      telefone=TELEFONE)
fabio   = Aluno.objects.create(empresa=emp2, nome="Fábio Zanella",        telefone=TELEFONE)
marina  = Aluno.objects.create(empresa=emp2, nome="Marina Colla",         telefone=TELEFONE)

# Alunos
alunos2_lista = []
for nome in ["Beatriz Tavares","Gabriel Ramos","Valentina Cruz","Lucas Freitas",
             "Isabela Nunes","Henrique Dias","Yasmin Torres","Felipe Moura",
             "Natália Costa","Eduardo Pinto","Clara Monteiro","Vitor Andrade",
             "Débora Lima","Rafael Soares","Priscila Gomes"]:
    alunos2_lista.append(
        Aluno.objects.create(empresa=emp2, nome=nome, telefone=TELEFONE)
    )

alunos_aula2 = alunos2_lista

# ── Cavalos emp2 ─────────────────────────────────────────────────────────────

# HOTELARIA (15)
c2_h = []
dados_hot2 = [
    ("Sultan",    ana_p,   "SIM", "Saudável",  480, baias2[0],  True),
    ("Esmeralda", cintia,  "NAO", "Saudável",  450, baias2[1],  True),
    ("Vendaval",  roberto, "SIM", "Alerta",    500, baias2[2],  True),
    ("Mística",   fabio,   "NAO", "Saudável",  430, baias2[3],  True),
    ("Tempestade",marina,  "SIM", "Saudável",  520, baias2[4],  True),
    ("Palomino",  ana_p,   "SIM", "Saudável",  490, baias2[5],  True),
    ("Serena",    cintia,  "NAO", "Saudável",  440, baias2[6],  False),
    ("Trovador",  roberto, "SIM", "Tratamento",470, baias2[7],  True),
    ("Nobleza",   fabio,   "NAO", "Saudável",  460, baias2[8],  True),
    ("Farrapo",   marina,  "SIM", "Alerta",    510, baias2[9],  True),
    ("Cigarra",   ana_p,   "NAO", "Saudável",  420, baias2[10], False),
    ("Titan",     cintia,  "SIM", "Saudável",  530, baias2[11], True),
    ("Primavera", roberto, "NAO", "Saudável",  450, baias2[12], True),
    ("Relâmpago", fabio,   "SIM", "Saudável",  500, baias2[13], True),
    ("Docinho",   marina,  "NAO", "Saudável",  410, baias2[14], False),
]
for nome, prop, ferr, status, peso, baia_obj, mat in dados_hot2:
    c = cav(emp2, nome, prop, "HOTELARIA", ferr, status, "BAIA",
            baia_obj=baia_obj, mat_proprio=mat, peso=peso, atividade="0.025")
    c2_h.append(c)

# Ocorrências hotelaria emp2
RegistroOcorrencia.objects.create(
    cavalo=c2_h[2],  # Vendaval
    titulo="Cólica espasmódica",
    descricao="Episódio de cólica tratado com dipirona e Buscopan. Sob observação.",
    veterinario="Dr. Márcio Pereira",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=3), time(22, 0))),
)
RegistroOcorrencia.objects.create(
    cavalo=c2_h[7],  # Trovador
    titulo="Pós-operatório fratura de costela",
    descricao="Fratura por trauma. Cirurgia realizada. Repouso 60 dias.",
    veterinario="Dra. Cristina Holtz",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=45), time(9, 0))),
)
RegistroOcorrencia.objects.create(
    cavalo=c2_h[9],  # Farrapo
    titulo="Lombalgia — dores coluna",
    descricao="Tratamento com infiltração. Fisioterapia 2x/semana.",
    veterinario="Dr. Márcio Pereira",
    data=timezone.make_aware(datetime.combine(HOJE - timedelta(days=10), time(10, 0))),
)

# PRÓPRIO (17)
nomes_prop2 = [
    ("Imperador", "SIM"), ("Galopeira", "NAO"), ("Horizonte", "SIM"),
    ("Ventania",  "NAO"), ("Maralto",   "SIM"), ("Caramelo",  "NAO"),
    ("Estrela",   "NAO"), ("Foguete",   "SIM"), ("Liberdade", "NAO"),
    ("Pampeiro",  "SIM"), ("Brisa",     "NAO"), ("Majestade", "SIM"),
    ("Cascata",   "NAO"), ("Noturno",   "SIM"), ("Serenata",  "NAO"),
    ("Campeão",   "SIM"), ("Miragem",   "NAO"),
]
c2_p = []
for i, (nome, ferr) in enumerate(nomes_prop2):
    c = cav(emp2, nome, hipica2, "PROPRIO", ferr, "Saudável", "BAIA",
            baia_obj=baias2[15 + i], atividade="0.025")
    c2_p.append(c)

# ── Manejo emp2 — valores seguros (dentro dos prazos configurados) ─────────
# Prazos: vacina=180d, vermifugo=90d, ferrageamento=45d, casqueamento=30d
todos_cavalos2 = c2_h + c2_p

# Ciclo de valores seguros para variedade sem risco de vencer
_vac_vals  = [20, 35, 50, 15, 40, 60, 25, 45, 10, 30, 55, 18, 38, 28, 48, 22, 42, 12, 33, 52, 16, 44, 27, 37, 19, 46, 23, 31, 53, 14, 41]
_verm_vals = [10, 25, 40, 15, 30, 50, 20, 35, 8,  22, 45, 12, 28, 18, 38, 14, 32, 7,  24, 42, 11, 36, 19, 29, 16, 44, 21, 26, 47, 9, 34]
_casco_vals= [5,  12, 18, 8,  15, 22, 10, 20, 6,  14, 25, 7,  16, 11, 23, 9,  17, 4,  13, 21, 8,  19, 12, 15, 6,  20, 10, 14, 22, 5, 18]
_ferr_vals = [8,  18, 28, 12, 22, 35, 15, 30, 6,  20, 40, 10, 25, 16, 32, 11, 27, 5,  21, 38, 9,  31, 14, 24, 7,  36, 13, 19, 42, 8, 26]

for i, c in enumerate(todos_cavalos2):
    if c.usa_ferradura == "SIM":
        set_manejo_em_dia(c, "SIM",
                          dias_atras_vacina=_vac_vals[i % len(_vac_vals)],
                          dias_atras_verm=_verm_vals[i % len(_verm_vals)],
                          dias_atras_ferr=_ferr_vals[i % len(_ferr_vals)])
    else:
        set_manejo_em_dia(c, "NAO",
                          dias_atras_vacina=_vac_vals[i % len(_vac_vals)],
                          dias_atras_verm=_verm_vals[i % len(_verm_vals)],
                          dias_atras_casco=_casco_vals[i % len(_casco_vals)])

# 2 com casqueamento próximo
for c in [c2_h[1], c2_p[1]]:  # Esmeralda, Galopeira
    c.ultimo_casqueamento = HOJE - timedelta(days=28)
    c.save()
# 4 com vermifugação próxima
for c in [c2_h[0], c2_h[4], c2_p[0], c2_p[2]]:  # Sultan, Tempestade, Imperador, Horizonte
    c.ultimo_vermifugo = HOJE - timedelta(days=89)
    c.save()

# Documentos emp2
for c in todos_cavalos2:
    vacinas_em_dia(c, meses_atras=random.randint(1, 4))

# 3 próximos de vencer + 1 vencido
DocumentoCavalo.objects.create(
    cavalo=c2_h[3], tipo="GTA", titulo="GTA Mística",
    data_validade=HOJE + timedelta(days=18),
)
DocumentoCavalo.objects.create(
    cavalo=c2_h[6], tipo="EXAME", titulo="Exame Mormo — Serena",
    data_validade=HOJE + timedelta(days=30),
)
DocumentoCavalo.objects.create(
    cavalo=c2_p[5], tipo="GTA", titulo="GTA Caramelo",
    data_validade=HOJE + timedelta(days=45),
)
DocumentoCavalo.objects.create(  # VENCIDO
    cavalo=c2_h[11], tipo="VACINA", titulo="Atestado Vacinação — Titan",
    data_validade=HOJE - timedelta(days=8),
)

# ── Estoque emp2 ──────────────────────────────────────────────────────────────
estoque2 = [
    ItemEstoque.objects.create(empresa=emp2, nome="Vermífugo Panacur",      quantidade_atual=3,  alerta_minimo=12, unidade="Doses",  consumo_diario=Decimal("0.4"), fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp2, nome="Ferraduras Traseiras",   quantidade_atual=5,  alerta_minimo=18, unidade="Pares",  consumo_diario=Decimal("0.6"), fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp2, nome="Agulhas Descartáveis",   quantidade_atual=10, alerta_minimo=40, unidade="Unid",   consumo_diario=Decimal("1.5"), fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp2, nome="Vacina Tétano",          quantidade_atual=2,  alerta_minimo=10, unidade="Doses",  consumo_diario=Decimal("0.2"), fornecedor_contato="5551991387872"),
    ItemEstoque.objects.create(empresa=emp2, nome="Ração Equi-S 30kg",      quantidade_atual=25, alerta_minimo=15, unidade="Sacos",  consumo_diario=Decimal("1.2")),
    ItemEstoque.objects.create(empresa=emp2, nome="Feno Tifton",            quantidade_atual=20, alerta_minimo=10, unidade="Fardos", consumo_diario=Decimal("1.0")),
    ItemEstoque.objects.create(empresa=emp2, nome="Suplemento Mineral",     quantidade_atual=15, alerta_minimo=5,  unidade="KG",     consumo_diario=Decimal("0.5")),
    ItemEstoque.objects.create(empresa=emp2, nome="Óleo de Coco Equino",    quantidade_atual=7,  alerta_minimo=3,  unidade="Litros", consumo_diario=Decimal("0.2")),
    ItemEstoque.objects.create(empresa=emp2, nome="Bandagem Elástica",      quantidade_atual=20, alerta_minimo=8,  unidade="Rolos"),
    ItemEstoque.objects.create(empresa=emp2, nome="Ungüento Hoof",          quantidade_atual=5,  alerta_minimo=2,  unidade="Potes"),
]

# ── Aulas emp2 ────────────────────────────────────────────────────────────────
cavalos_aula2 = [c for c in c2_h + c2_p
                 if c.status_saude in ("Saudável",) and c.nome not in ("Trovador",)]

print("📅 Gerando aulas Hípica Cavalos do Sul...")
d = INICIO
while d <= FIM:
    if d.weekday() != 6:
        n_aulas = random.randint(3, 7)
        horarios_usados = set()
        for _ in range(n_aulas):
            hora = random.choice([7, 8, 9, 10, 14, 15, 16, 17])
            if hora in horarios_usados:
                continue
            horarios_usados.add(hora)
            aluno  = random.choice(alunos_aula2)
            cavalo = random.choice(cavalos_aula2)
            Aula.objects.create(
                empresa=emp2,
                aluno=aluno,
                cavalo=cavalo,
                instrutor=random.choice(instrutores2),
                tipo=random.choice(["NORMAL", "NORMAL", "RECUPERAR"]),
                data_hora=timezone.make_aware(datetime.combine(d, time(hora, 0))),
                local=random.choice(locais),
                concluida=(d < HOJE),
            )
    d += timedelta(days=1)

# ── Financeiro emp2 ───────────────────────────────────────────────────────────

print("💰 Gerando financeiro Hípica Cavalos do Sul...")
meses_vistos2 = set()
m = INICIO
while m <= FIM:
    chave = (m.year, m.month)
    if chave not in meses_vistos2:
        meses_vistos2.add(chave)
        MovimentacaoFinanceira.objects.create(
            empresa=emp2,
            data=date(m.year, m.month, 5),
            tipo="Receita",
            descricao="Mensalidades de hotelaria",
            valor=Decimal(random.randint(12000, 16000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp2,
            data=date(m.year, m.month, 5),
            tipo="Receita",
            descricao="Aulas e treinos",
            valor=Decimal(random.randint(3500, 6000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp2,
            data=date(m.year, m.month, 10),
            tipo="Despesa",
            descricao="Ração e insumos",
            valor=Decimal(random.randint(4500, 7500)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp2,
            data=date(m.year, m.month, 15),
            tipo="Despesa",
            descricao="Veterinário e medicamentos",
            valor=Decimal(random.randint(1200, 3000)),
        )
        MovimentacaoFinanceira.objects.create(
            empresa=emp2,
            data=date(m.year, m.month, 20),
            tipo="Despesa",
            descricao="Salários e encargos",
            valor=Decimal(random.randint(5500, 8500)),
        )
    m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)

print("✅ Hípica Cavalos do Sul populado.")

# ─────────────────────────────────────────────────────────────────────────────
# 8. RESUMO FINAL
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print("✅ BASE GERADA COM SUCESSO")
print("="*60)
print(f"  Empresas:    {Empresa.objects.count()}")
print(f"  Usuários:    {User.objects.count()}")
print(f"  Perfis:      {Perfil.objects.count()}")
print(f"  Alunos:      {Aluno.objects.count()}")
print(f"  Cavalos:     {Cavalo.objects.count()}")
print(f"  Documentos:  {DocumentoCavalo.objects.count()}")
print(f"  Ocorrências: {RegistroOcorrencia.objects.count()}")
print(f"  Estoques:    {ItemEstoque.objects.count()}")
print(f"  Aulas:       {Aula.objects.count()}")
print(f"  Financeiro:  {MovimentacaoFinanceira.objects.count()}")
print("="*60)
print("\n🔐 CREDENCIAIS:")
print("  AdminGate  / DadoManco$29   (superuser)")
print("  Gate4      / Gate2026")
print("  gestor_hipica  / DadoManco$29  → Haras Elite Prateada")
print("  gestor_hipica1 / DadoManco$29  → Hípica Cavalos do Sul")
print("  Suzana     / Asterix         → Professora emp1")
print("  Alessandro / Gate2026        → Professor emp1")
print("  LuizaSqueff/ Gate2026        → Professora emp1")
print("  Aluno33    / Aluno$2026      → Aluno emp1")
print("="*60)
