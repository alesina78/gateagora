# seed_farrapos.py: massa de teste no Clube Farrapos. Só cria registros, não apaga nada.
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone

from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, RacaCavalo, Aula,
    ConfirmacaoPresenca, Fatura, ItemFatura, Fornecedor, ItemEstoque,
)

random.seed(42)
emp = Empresa.objects.filter(nome="Clube Farrapos").first()
if emp is None:
    raise SystemExit("Empresa 'Clube Farrapos' não encontrada. Nada foi criado.")
if Aluno.objects.filter(empresa=emp, nome="Trovão").exists():
    raise SystemExit("Massa de teste já existe. Nada foi criado.")

hoje = timezone.localdate()
ATLETAS = ["Trovão", "Tinho", "Pé de Vento", "Tanque", "Tedesco", "Corvo", "Pedrito",
           "Filhote do Pedrito", "Boca Doce", "Vovô Raio", "Vovô Cometa", "Pescoço Longo",
           "Pescocinho do Vale", "Portão 1", "Portão 2"]
CAVALOS = ["Dadinho", "Formiga Atômica", "Estileto", "Lindóia", "Chacal", "Barrabás",
           "Cripton", "Proteus", "Zeus", "Golias", "Alabama", "Jaboti", "Mrs Magoo"]
MESES = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]


def dia28_do_mes_seguinte(d):
    ano = d.year + (1 if d.month == 12 else 0)
    mes = 1 if d.month == 12 else d.month + 1
    return date(ano, mes, 28)


# Professor de teste
prof_user, _ = User.objects.get_or_create(
    username="demo_professor", defaults={"first_name": "Professor", "last_name": "Demo"})
prof, _ = Perfil.objects.get_or_create(user=prof_user, defaults={"empresa": emp, "cargo": "Professor"})

racas = [RacaCavalo.objects.get_or_create(nome=n)[0] for n in
         ["Mangalarga Marchador", "Quarto de Milha", "Crioulo",
          "Puro Sangue Lusitano", "Cavalo de Hipismo (BH)"]]

# Atletas
alunos = [Aluno.objects.create(
            empresa=emp, nome=n, telefone=f"5199999{i:04d}", ativo=True,
            valor_aula=Decimal(random.choice(["120.00", "150.00", "180.00"])))
          for i, n in enumerate(ATLETAS)]

# Cavalos: um para cada um dos primeiros atletas
STATUS = ["Saudavel"] * 5 + ["Alerta", "Tratamento", "Doente"]
cavalos = []
for i, nome in enumerate(CAVALOS):
    if i % 2 == 0:
        baia = Baia.objects.create(empresa=emp, numero=200 + i)
        piquete, onde = None, "BAIA"
    else:
        baia = None
        piquete = Piquete.objects.create(empresa=emp, nome=f"Piquete Demo {i}", capacidade=4)
        onde = "PIQUETE"
    cavalos.append(Cavalo.objects.create(
        empresa=emp, nome=nome, proprietario=alunos[i],
        categoria="HOTELARIA" if i % 3 else "PROPRIO",
        status_saude=random.choice(STATUS), onde_dorme=onde,
        baia=baia, piquete=piquete, raca=random.choice(racas),
        peso=float(random.randint(420, 560)),
        fator_atividade=random.choice(["0.018", "0.025", "0.035"]),
        usa_ferradura=random.choice(["SIM", "NAO"]),
        ultima_vacina=hoje - timedelta(days=random.randint(30, 420)),
        ultimo_vermifugo=hoje - timedelta(days=random.randint(20, 200)),
        ultimo_ferrageamento=hoje - timedelta(days=random.randint(10, 90)),
        ultimo_casqueamento=hoje - timedelta(days=random.randint(10, 90)),
        ultima_troca_cama=hoje - timedelta(days=random.randint(5, 60)),
        mensalidade_baia=Decimal(random.choice(["900.00", "1100.00", "1200.00"])),
        racao_tipo="Guabi Equi-S", racao_qtd_manha="2kg", racao_qtd_noite="1.5kg",
        feno_tipo="Coast Cross", feno_qtd="À vontade",
    ))

# Aulas de agosto a outubro, com confirmação e faturas de consumo
n_aulas = 0
for i, cav in enumerate(cavalos):
    aluno = cav.proprietario
    for comp in MESES:
        concluidas = []
        for _ in range(2):
            dia = comp + timedelta(days=random.randint(0, 27))
            if dia > hoje + timedelta(days=10):
                continue
            dh = timezone.make_aware(datetime(dia.year, dia.month, dia.day,
                                              random.choice([8, 9, 10, 14, 15]),
                                              random.choice([0, 30])))
            aula = Aula.objects.create(
                empresa=emp, aluno=aluno, cavalo=cav, instrutor=prof,
                data_hora=dh, local="picadeiro_1", tipo="NORMAL",
                concluida=dia < hoje)
            n_aulas += 1
            if random.random() < 0.8:
                ConfirmacaoPresenca.objects.create(aula=aula, aluno=aluno)
            if aula.concluida:
                concluidas.append(aula)
        if concluidas:
            venc = dia28_do_mes_seguinte(comp)
            f = Fatura.objects.create(
                empresa=emp, aluno=aluno, tipo="CONSUMO", competencia=comp,
                data_vencimento=venc, valor=Decimal("0.00"),
                status="PAGO" if venc < hoje else "PENDENTE")
            for aula in concluidas:
                ItemFatura.objects.create(
                    fatura=f, tipo="AULA", cavalo=cav,
                    descricao=f"Aula — {aula.data_hora:%d/%m/%Y}",
                    valor=aluno.valor_aula, data=aula.data_hora.date())

# Mensalidade de baia (fatura fixa, uma por cavalo e mês)
for cav in cavalos:
    for comp in MESES:
        venc = date(comp.year, comp.month, 28)
        f = Fatura.objects.create(
            empresa=emp, aluno=cav.proprietario, tipo="FIXA", competencia=comp,
            data_vencimento=venc, valor=Decimal("0.00"),
            status="PAGO" if venc < hoje else "PENDENTE")
        ItemFatura.objects.create(
            fatura=f, tipo="BAIA", cavalo=cav,
            descricao=f"Mensalidade baia — {cav.nome} — {comp:%m/%Y}",
            valor=cav.mensalidade_baia, data=venc)

# Fornecedores
f1 = Fornecedor.objects.create(
    empresa=emp, nome="Maragato Rações", telefone="5151999990001",
    frete_aproximado=Decimal("40.00"), frete_ultima_entrega=Decimal("35.00"),
    data_ultima_entrega=hoje - timedelta(days=20), prazo_entrega_dias=7,
    frete_gratis_acima=Decimal("1000.00"), pedido_minimo_quantidade=5)
f2 = Fornecedor.objects.create(
    empresa=emp, nome="Armazém do Campo", telefone="5151999990002",
    frete_aproximado=Decimal("0.00"), prazo_entrega_dias=3, aceita_retirada=True)

# Estoque: (nome, unidade, consumo/dia, mínimo, preço, cobertura, validade, embalagem, fornecedor)
ESTOQUE = [
    ("Ração Premium 25kg", "Sacos", "2", 15, "120.00", 30, 60, 1, f1),
    ("Feno Coast Cross 20kg", "Fardos", "3", 10, "28.00", 60, 90, 1, f2),
    ("Maravalha 20kg", "Sacos", "1", 8, "22.00", 45, None, 1, f2),
    ("Seringas Descartáveis", "Unid", "3", 50, "0.90", 60, 365, 10, f1),
    ("Vacina Influenza", "Doses", "0.5", 15, "45.00", 90, 120, 5, f1),
    ("Ferradura", "Pares", "0.2", 20, "38.00", 60, None, 2, f2),
]
for nome, unid, cons, minimo, preco, cob, val, emb, forn in ESTOQUE:
    ItemEstoque.objects.create(
        empresa=emp, nome=nome, unidade=unid, consumo_diario=Decimal(cons),
        alerta_minimo=minimo, preco_unitario=Decimal(preco), dias_cobertura=cob,
        dias_validade=val, tamanho_embalagem=emb, fornecedor_padrao=forn,
        quantidade_atual=minimo * 2)

print(f"Atletas: {len(alunos)} | Cavalos: {len(cavalos)} | Aulas: {n_aulas} | "
      f"Faturas: {Fatura.objects.filter(empresa=emp).count()} | "
      f"Itens de estoque: {ItemEstoque.objects.filter(empresa=emp).count()}")
