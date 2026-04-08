"""
Seed completo Gate 4
Apaga tudo e recria base fictícia realista
Período: 01/11/2025 → 30/04/2026
"""

from datetime import date, datetime, timedelta, time
from decimal import Decimal
import random

from django.utils import timezone
from django.contrib.auth.models import User

from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Aula,
    DocumentoCavalo, RegistroOcorrencia,
    ItemEstoque, MovimentacaoFinanceira,
    ConfigPrazoManejo
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================
TELEFONE = "+5551991387872"
INICIO = date(2025, 11, 1)
FIM = date(2026, 4, 30)

random.seed(42)

# =====================================================
# LIMPEZA TOTAL (ordem segura)
# =====================================================
Aula.objects.all().delete()
DocumentoCavalo.objects.all().delete()
RegistroOcorrencia.objects.all().delete()
MovimentacaoFinanceira.objects.all().delete()
ItemEstoque.objects.all().delete()
Cavalo.objects.all().delete()
Aluno.objects.all().delete()
Perfil.objects.all().delete()
Empresa.objects.all().delete()
User.objects.all().delete()

# =====================================================
# EMPRESAS
# =====================================================
empresas = [
    Empresa.objects.create(nome="Hípica Estrela do Sul", slug="hipica-estrela"),
    Empresa.objects.create(nome="Haras Santa Aurora", slug="haras-santa-aurora"),
]

# =====================================================
# PRAZOS DE MANEJO
# =====================================================
for emp in empresas:
    ConfigPrazoManejo.objects.create(
        empresa=emp,
        prazo_vacina=180,
        prazo_vermifugo=90,
        prazo_ferrageamento=45,
        prazo_casqueamento=30,
    )

# =====================================================
# FUNÇÃO USUÁRIO + PERFIL
# =====================================================
def criar_usuario(username, senha, *, empresa=None, cargo=None, superuser=False):
    u = User.objects.create(
        username=username,
        is_superuser=superuser,
        is_staff=True,
        is_active=True,
    )
    u.set_password(senha)
    u.save()

    if empresa:
        Perfil.objects.create(
            user=u,
            empresa=empresa,
            cargo=cargo,
            telefone=TELEFONE
        )

    return u

# =====================================================
# USUÁRIOS
# =====================================================
criar_usuario("AdminGate", "DadoManco$29", superuser=True)
criar_usuario("Gate4", "Gate2026")

for emp in empresas:
    criar_usuario("gestor_hipica1", "DadoManco$29", empresa=emp, cargo="GESTOR")
    criar_usuario("Suzana", "Asterix", empresa=emp, cargo="ATENDENTE")
    criar_usuario("Aluno33", "Aluno$2026", empresa=emp, cargo="ALUNO")

# =====================================================
# DADOS POR EMPRESA
# =====================================================
for emp in empresas:
    hoje = timezone.localdate()

    # Aluno institucional (dono dos cavalos próprios)
    institucional = Aluno.objects.create(
        empresa=emp,
        nome=emp.nome,
        telefone=TELEFONE,
        ativo=True
    )

    donos = []
    for nome in ["Carlos Menezes","Fernanda Lopes","Ricardo Motta","Juliana Reis","Paulo Teixeira"]:
        donos.append(
            Aluno.objects.create(
                empresa=emp,
                nome=nome,
                telefone=TELEFONE,
                ativo=True
            )
        )

    alunos = donos[:]
    for nome in ["Ana","Bruno","Diego","Larissa","Marcos","Renata","Tiago","Sofia","Pedro"]:
        alunos.append(
            Aluno.objects.create(
                empresa=emp,
                nome=f"{nome} Silva",
                telefone=TELEFONE,
                ativo=True
            )
        )

    # =================================================
    # CAVALOS
    # =================================================
    cavalos = []
    for i in range(32):
        proprio = i < 17
        cav = Cavalo.objects.create(
            empresa=emp,
            nome=f"Cavalo {i+1}",
            proprietario=donos[i % 5] if proprio else institucional,
            categoria="PROPRIO" if proprio else "HOTELARIA",
            material_proprio=(i < 2),
        )
        cavalos.append(cav)

    # Casqueio e vermífugo próximos
    for c in cavalos[:2]:
        c.ultimo_casqueamento = hoje - timedelta(days=27)
        c.save()

    for c in cavalos[2:6]:
        c.ultimo_vermifugo = hoje - timedelta(days=88)
        c.save()

    # Problemas veterinários
    for c in cavalos[6:9]:
        RegistroOcorrencia.objects.create(
            cavalo=c,
            data=hoje - timedelta(days=2),
            titulo="Claudicação leve",
            descricao="Monitorar evolução",
        )

    # =================================================
    # DOCUMENTOS
    # =================================================
    DocumentoCavalo.objects.create(
        cavalo=cavalos[0],
        tipo="GTA",
        titulo="GTA Novembro",
        data_validade=hoje - timedelta(days=1)
    )

    for c in cavalos[1:4]:
        DocumentoCavalo.objects.create(
            cavalo=c,
            tipo="ANEMIA",
            titulo="Exame de rotina",
            data_validade=hoje + timedelta(days=4)
        )

    # =================================================
    # ESTOQUE
    # =================================================
    for nome, qtd in [
        ("Ração Premium", 10),
        ("Vermífugo", 2),
        ("Ferraduras", 5),
        ("Seringas", 20),
    ]:
        ItemEstoque.objects.create(
            empresa=emp,
            nome=nome,
            quantidade_atual=qtd,
            alerta_minimo=15,
        )

    # =================================================
    # AULAS / TREINOS (sem domingos)
    # =================================================
    d = INICIO
    while d <= FIM:
        if d.weekday() != 6:  # domingo
            for h in range(random.randint(3, 5)):
                Aula.objects.create(
                    empresa=emp,
                    aluno=random.choice(alunos),
                    cavalo=random.choice(cavalos),
                    tipo="TREINO",
                    data_hora=timezone.make_aware(
                        datetime.combine(d, time(8 + h, 0))
                    )
                )
        d += timedelta(days=1)

    # =================================================
    # FINANCEIRO (mensal, data única)
    # =================================================
    m = INICIO
    while m <= FIM:
        MovimentacaoFinanceira.objects.create(
            empresa=emp,
            data=date(m.year, m.month, 5),
            tipo="RECEITA",
            descricao="Mensalidades",
            valor=Decimal(random.randint(8000, 12000))
        )
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)

print("✅ Base completa gerada com sucesso.")