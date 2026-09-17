# -*- coding: utf-8 -*-
"""
populate_gateagora.py — compatível com seu models.py atual:
- NÃO usa campos removidos de Cavalo
- Usa timezone.make_aware (sem .localize)
- Cria Admin e Admin4 (Gestores) e instrutor1 (Professor)
- Cria Hípica Paraíso RS (slug='hprs') e dados completos

Como executar (PowerShell):
    py manage.py shell -c "exec(open('populate_gateagora.py','r',encoding='utf-8').read())"
"""

import random
from decimal import Decimal
from datetime import date, datetime, time, timedelta

from django.utils import timezone
from django.contrib.auth.models import User

from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo, Aula,
    ItemEstoque, MovimentacaoFinanceira, DocumentoCavalo, RegistroOcorrencia
)

# ---------------------------
# Parâmetros/ajustes gerais
# ---------------------------
random.seed(20260303)
INICIO = date(2025, 11, 1)
FIM = date(2026, 3, 30)
HOJE = timezone.localdate()

def aware(dt_naive: datetime):
    """Converte datetime 'naive' para timezone atual."""
    return timezone.make_aware(dt_naive, timezone.get_current_timezone())


# ---------------------------
# Reset seguro da empresa
# ---------------------------
Empresa.objects.filter(slug='hprs').delete()


# ---------------------------
# Empresa
# ---------------------------
empresa = Empresa.objects.create(
    nome='Hípica Paraíso RS',
    cidade='Porto Alegre',
    slug='hprs',
)


# ---------------------------
# Usuários e Perfis
# ---------------------------
def ensure_user(username, email, password='Gate$2024', staff=True, superuser=False, cargo='Tratador'):
    """
    Garante o User e seu Perfil (empresa + cargo). Retorna (user, perfil).
    """
    u, _ = User.objects.get_or_create(username=username, defaults={'email': email})
    if not u.has_usable_password():
        u.set_password(password)
    u.is_staff = staff
    u.is_superuser = superuser
    u.save()

    p, _ = Perfil.objects.get_or_create(user=u, defaults={'empresa': empresa, 'cargo': cargo})
    # Garante que o perfil aponte para a empresa/cargo corretos
    p.empresa = empresa
    p.cargo = cargo
    p.save()
    return u, p

# Gestores
ensure_user('Admin4', 'admin4@hprs.test', superuser=True, cargo='Gestor')
ensure_user('Admin',  'gateagora@gmail.com', superuser=True, cargo='Gestor')

# Professor
_, prof_perfil = ensure_user('instrutor1', 'instrutor1@hprs.test', staff=True, superuser=False, cargo='Professor')


# ---------------------------
# Alunos
# ---------------------------
nomes_alunos = [
    'Maria Figueiredo','Julia Campos','Bianca Azevedo','Pedro Souza','Ricardo Menezes',
    'Caio Barcellos','Fernanda Dias','Hector Martins','Beatriz Morais','Larissa Melo',
    'Rafael Queiroz','Sofia Almeida','Gustavo Teixeira','Camila Nogueira','Lucas Ferraz',
    'Isabela Couto','Thiago Moura','Bruna Carvalho','André Ribeiro','Paula Tavares',
    'Felipe Duarte','Natália Peixoto','Eduardo Paiva','Carolina Sampaio','Henrique Prado',
    'Aline Borges','Rodrigo Leal','Tatiane Porto','Bruno Amaral','Daniele Mota'
]

alunos = []
for nome in nomes_alunos:
    tel = f"55{random.randint(11, 99)}9{random.randint(10000000, 99999999)}"
    a = Aluno.objects.create(
        empresa=empresa,
        nome=nome,
        telefone=tel,
        ativo=True,
        valor_aula=Decimal(random.choice([150, 160, 170, 180]))
    )
    alunos.append(a)

# Aluno institucional (para cavalos PRÓPRIO/Escola)
aluno_escola = Aluno.objects.create(
    empresa=empresa,
    nome='Escola HPRS',
    telefone='559900000000',
    ativo=True,
    valor_aula=Decimal('0.00')
)


# ---------------------------
# Baias e Piquetes
# ---------------------------
baias = []
for n in range(1, 25):  # 24 baias
    baias.append(Baia.objects.create(empresa=empresa, numero=f"{n:02d}", status='Livre'))

piquetes_info = [
    ('Piquete Norte', 4),
    ('Piquete Sul', 4),
    ('Piquete Leste', 4),
    ('Piquete Oeste', 5),
    ('Piquete Central', 3),
    ('Piquete Rio', 4),
]
piquetes = []
for nome, cap in piquetes_info:
    piquetes.append(Piquete.objects.create(empresa=empresa, nome=nome, capacidade=cap, status='Livre'))


# ---------------------------
# Cavalos (30)
# ---------------------------
nomes_cavalos = [
    'Relâmpago','Ventania','Fumaça','Orion','Estelar','Thor','Zeus','Apolo','Galante','Trovão',
    'Horizonte','Centauro','Cometa','Espírito','Corcel','Pegasus','Alado','Valente','Astro','Boreal',
    'Gaia','Hércules','Argos','Celer','Sirius','Nobre','Rubi','Onyx','Vulcano','Bravio'
]

cavalos = []
for idx, nome in enumerate(nomes_cavalos):
    if idx < 15:
        categoria = 'PROPRIO'
        proprietario = aluno_escola
    else:
        categoria = 'HOTELARIA'
        proprietario = random.choice(alunos)

    onde_dorme = 'BAIA' if idx < 20 else 'PIQUETE'

    cavalo = Cavalo.objects.create(
        empresa=empresa,
        nome=nome,
        categoria=categoria,
        status_saude=random.choice(['Saudável']*6 + ['Alerta']*2 + ['Doente']),
        onde_dorme=onde_dorme,

        # IA/Raça/Atividade
        raca=random.choice(['mang_marchador','quarto_milha','psl','crioulo','hipismo','srd']),
        peso=random.choice([420, 450, 480, 500, 520, 540]),
        fator_atividade=random.choice(['0.018','0.025','0.035']),

        # Equipamentos
        tipo_sela=random.choice(['Sela Salto Americana','Sela Mista','Sela de Adestramento','']),
        tipo_cabecada=random.choice(['Cabeçada com Freio D','Cabeçada simples','Bridão','']),
        material_proprio=random.choice([True, False, False]),

        # Propriedade
        proprietario=proprietario,

        # Saúde (apenas campos atuais do modelo)
        ultima_vacina=HOJE - timedelta(days=random.randint(10, 90)),
        ultimo_ferrageamento=HOJE - timedelta(days=random.randint(10, 60)),

        # Plano alimentar
        racao_tipo=random.choice(['Guabi Equi-S','Purina Pro','NutriHorse','']),
        racao_qtd_manha=random.choice(['1,5 kg','2 kg','2,5 kg','']),
        racao_qtd_noite=random.choice(['1,5 kg','2 kg','2,5 kg','']),
        feno_tipo=random.choice(['Coast Cross','Tifton 85','Alfafa']),
        feno_qtd=random.choice(['À vontade','3 fardos/dia','4 fardos/dia']),
        complemento_nutricional=random.choice(['','Vitamina B12','Biotina','Ômega 3']),

        mensalidade_baia=Decimal(random.choice([900, 1000, 1200, 1500, 1800])),
    )
    cavalos.append(cavalo)

# Aloca 20 cavalos nas 20 primeiras baias
for cavalo, baia in zip(cavalos[:20], baias[:20]):
    cavalo.baia = baia
    cavalo.save(update_fields=['baia'])
    baia.status = 'Ocupada'
    baia.save(update_fields=['status'])

# Aloca 10 cavalos em piquetes
for cavalo, piq in zip(cavalos[20:], piquetes * 2):
    cavalo.piquete = piq
    cavalo.save(update_fields=['piquete'])

for p in piquetes:
    if Cavalo.objects.filter(empresa=empresa, piquete=p).exists():
        p.status = 'Ocupado'
        p.save(update_fields=['status'])


# ---------------------------
# Documentos (alguns a vencer)
# ---------------------------
tipos_doc = ['GTA','VACINA','EXAME','OUTRO']
for cavalo in random.sample(cavalos, 15):
    for t in random.sample(tipos_doc, k=2):
        # 40%: vencendo em 30 dias; 60%: 2~6 meses
        if random.random() < 0.4:
            validade = HOJE + timedelta(days=random.randint(1, 30))
        else:
            validade = HOJE + timedelta(days=random.randint(60, 180))
        DocumentoCavalo.objects.create(
            cavalo=cavalo,
            tipo=t,
            data_validade=validade,
        )


# ---------------------------
# Ocorrências (prontuário)
# ---------------------------
for cavalo in random.sample(cavalos, 6):
    RegistroOcorrencia.objects.create(
        cavalo=cavalo,
        data=timezone.now() - timedelta(days=random.randint(1, 40)),
        titulo=random.choice(['Claudicação leve','Ajuste ferrageamento','Avaliação odontológica','Consulta preventiva']),
        descricao='Observações registradas pela equipe. Recomendado monitorar nos próximos dias.',
        veterinario=random.choice(['Dr. Silva','Dra. Costa','']),
    )


# ---------------------------
# Aulas (01/11/2025 → 30/03/2026)
# seg..sáb; 3–6 por dia
# ---------------------------
Aula.objects.filter(empresa=empresa).delete()

horarios = [time(9,0), time(10,0), time(11,0), time(14,0), time(15,0), time(16,30)]
def num_por_dia():
    return random.randint(3, 6)

dia = INICIO
while dia <= FIM:
    if dia.weekday() <= 5:  # 0..5 = seg..sáb
        for h in sorted(random.sample(horarios, k=num_por_dia())):
            aluno = random.choice(alunos)
            cavs_do_aluno = Cavalo.objects.filter(empresa=empresa, proprietario=aluno)
            cavalo = random.choice(list(cavs_do_aluno)) if cavs_do_aluno.exists() else random.choice(cavalos)

            Aula.objects.create(
                empresa=empresa,
                aluno=aluno,
                cavalo=cavalo,
                instrutor=prof_perfil,  # Perfil (Professor)
                data_hora=aware(datetime.combine(dia, h)),
                local=random.choice(['picadeiro_1','picadeiro_2','pista_salto']),
                tipo=random.choice(['NORMAL']*5 + ['RECUPERAR']),
                concluida=(dia < HOJE),
                relatorio_treino='Aquecimento, exercícios técnicos e desaquecimento.',
            )
    dia += timedelta(days=1)


# ---------------------------
# Itens de Estoque
# ---------------------------
ItemEstoque.objects.filter(empresa=empresa).delete()
for nome, qtd, min_q, unid, forn in [
    ('Ração Guabi Equi-S', 12, 5, 'Sacos', '55999772211'),
    ('Feno Coast Cross', 30, 10, 'Fardos', '55999112233'),
    ('Feno Alfafa', 18, 8, 'Fardos', '55998121212'),
    ('Vermífugo Ouro Fino', 6, 2, 'Unidade', '55999444555'),
    ('Soro Vitaminado', 3, 1, 'Unidade', '55999221100'),
    ('Ferraduras', 10, 4, 'Unidade', '55999884433'),
]:
    ItemEstoque.objects.create(
        empresa=empresa,
        nome=nome,
        quantidade_atual=qtd,
        alerta_minimo=min_q,
        unidade=unid,
        fornecedor_contato=forn
    )


# ---------------------------
# Financeiro (nov/25..mar/26)
# ---------------------------
MovimentacaoFinanceira.objects.filter(empresa=empresa).delete()
for ano, mes in [(2025,11), (2025,12), (2026,1), (2026,2), (2026,3)]:
    # Receita: hotelaria (soma das mensalidades de cavalos HOTELARIA)
    total_hotelaria = sum(float(c.mensalidade_baia) for c in cavalos if c.categoria == 'HOTELARIA')
    MovimentacaoFinanceira.objects.create(
        empresa=empresa,
        tipo='Receita',
        descricao=f"Mensalidades Hotelaria {mes:02d}/{ano}",
        valor=Decimal(total_hotelaria),
        data=date(ano, mes, min(5, (date(ano, mes, 1) + timedelta(days=4)).day)),  # ~dia 05
    )

    # Receita: aulas concluídas do mês (~ticket médio 160)
    aulas_mes = Aula.objects.filter(
        empresa=empresa, concluida=True,
        data_hora__year=ano, data_hora__month=mes
    ).count()
    MovimentacaoFinanceira.objects.create(
        empresa=empresa,
        tipo='Receita',
        descricao=f"Aulas {mes:02d}/{ano}",
        valor=Decimal(aulas_mes * 160),
        data=date(ano, mes, min(28, 20)),  # ~dia 20
    )

    # Despesas do mês
    for desc, base in [
        ('Compra de Ração', 1200),
        ('Compra de Feno', 1400),
        ('Ferrageamento', 500),
        ('Veterinário', 600),
        ('Manutenção', 350),
    ]:
        MovimentacaoFinanceira.objects.create(
            empresa=empresa,
            tipo='Despesa',
            descricao=f"{desc} {mes:02d}/{ano}",
            valor=Decimal(base + random.randint(-100, 150)),
            data=date(ano, mes, random.randint(8, 18)),
        )


# ---------------------------
# Resumo final no console
# ---------------------------
print("\n✅ População concluída com sucesso!")
print("Empresa:", empresa.nome, f"(slug={empresa.slug})")
print("Alunos:", Aluno.objects.filter(empresa=empresa).count())
print("Baias:", Baia.objects.filter(empresa=empresa).count())
print("Piquetes:", Piquete.objects.filter(empresa=empresa).count())
print("Cavalos:", Cavalo.objects.filter(empresa=empresa).count())
print("Aulas:", Aula.objects.filter(empresa=empresa).count())
print("Estoque:", ItemEstoque.objects.filter(empresa=empresa).count())
print("Documentos:", DocumentoCavalo.objects.filter(cavalo__empresa=empresa).count())
print("Ocorrências:", RegistroOcorrencia.objects.filter(cavalo__empresa=empresa).count())