# seed_farrapos_v2.py: complementa a massa do Clube Farrapos. Só cria registros.
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.utils import timezone

from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Piquete, Aula, ConfirmacaoPresenca,
    Sela, Cabecada, ItemEstoque, LoteEstoque, MovimentacaoEstoque,
    MovimentacaoFinanceira, Plano, DocumentoCavalo, RegistroOcorrencia,
    EventoAgendaCavalo,
)

random.seed(7)
emp = Empresa.objects.filter(nome="Clube Farrapos").first()
if emp is None:
    raise SystemExit("Empresa 'Clube Farrapos' não encontrada. Nada foi criado.")
if LoteEstoque.objects.filter(item__empresa=emp).exists():
    raise SystemExit("Complemento já aplicado. Nada foi criado.")

hoje = timezone.localdate()
prof = Perfil.objects.filter(empresa=emp, cargo="Professor").first()
if prof is None:
    raise SystemExit("Professor demo não encontrado. Rode o seed_farrapos.py antes.")


def aware(d, h=9):
    return timezone.make_aware(datetime(d.year, d.month, d.day, h, 0))


MESES = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]

# 1. Selas e cabeçadas, distribuídas entre os cavalos
selas = [Sela.objects.create(nome=n, descricao="Demo") for n in
         ["Sela preta cernelha alta", "Sela de salto", "Sela americana"]]
cabecadas = [Cabecada.objects.create(nome=n, descricao="Demo") for n in
             ["Cabeçada preta", "Cabeçada marrom bridão", "Cabeçada de cordas"]]
cavalos = list(Cavalo.objects.filter(empresa=emp).order_by("id"))
for i, cav in enumerate(cavalos):
    cav.sela_padrao = selas[i % 3]
    cav.cabecada_padrao = cabecadas[i % 3]
    cav.save(update_fields=["sela_padrao", "cabecada_padrao"])

# 2. Atletas sem cavalo ganham um cavalo, com aulas nos três meses
for n, aluno in enumerate(Aluno.objects.filter(empresa=emp, cavalos__isnull=True), start=1):
    piq = Piquete.objects.create(empresa=emp, nome=f"Piquete Extra {n}", capacidade=4)
    cav = Cavalo.objects.create(
        empresa=emp, nome=f"Cavalo Demo {n}", proprietario=aluno,
        categoria="HOTELARIA", status_saude="Saudavel", onde_dorme="PIQUETE",
        piquete=piq, peso=470.0, fator_atividade="0.025", usa_ferradura="NAO",
        ultima_vacina=hoje - timedelta(days=60), ultimo_vermifugo=hoje - timedelta(days=40),
        mensalidade_baia=Decimal("900.00"),
        sela_padrao=selas[n % 3], cabecada_padrao=cabecadas[n % 3])
    cavalos.append(cav)
    for mes in MESES:
        for _ in range(2):
            dia = mes + timedelta(days=random.randint(0, 27))
            if dia > hoje + timedelta(days=10):
                continue
            a = Aula.objects.create(
                empresa=emp, aluno=aluno, cavalo=cav, instrutor=prof,
                data_hora=aware(dia, random.choice([8, 9, 10, 14, 15])),
                local="picadeiro_1", tipo="NORMAL", concluida=dia < hoje)
            if random.random() < 0.8:
                ConfirmacaoPresenca.objects.create(aula=a, aluno=aluno)

# 3. Estoque: lotes (vencido, a vencer e válido) e histórico de movimentações
for item in ItemEstoque.objects.filter(empresa=emp):
    consumo = float(item.consumo_diario or 1)
    minimo = float(item.alerta_minimo or 5)
    LoteEstoque.objects.create(item=item, quantidade=Decimal(str(round(consumo * 5, 2))),
                               data_validade=hoje - timedelta(days=10), numero_lote="VENC-01")
    LoteEstoque.objects.create(item=item, quantidade=Decimal(str(round(minimo * 0.6, 2))),
                               data_validade=hoje + timedelta(days=15), numero_lote="A-VENCER-01")
    LoteEstoque.objects.create(item=item, quantidade=Decimal(str(round(minimo * 1.5, 2))),
                               data_validade=hoje + timedelta(days=120), numero_lote="OK-01")
    item.quantidade_atual = int(minimo * 2.1)
    item.save(update_fields=["quantidade_atual"])
    for mes in MESES:
        if mes <= hoje:
            MovimentacaoEstoque.objects.create(
                empresa=emp, item=item, data=mes + timedelta(days=2),
                quantidade=Decimal(str(round(consumo * 30, 2))), tipo="entrada",
                observacao="Compra demo")
        for semana in range(4):
            d = mes + timedelta(days=7 * semana + 1)
            if d <= hoje:
                MovimentacaoEstoque.objects.create(
                    empresa=emp, item=item, data=d,
                    quantidade=Decimal(str(round(consumo * 7, 2))), tipo="saida",
                    observacao="Consumo semanal demo")

# 4. Financeiro: receitas e despesas por mês (só até hoje)
for mes in MESES:
    lancamentos = [
        ("Receita", "Mensalidades de baia recebidas", "9800.00", 5),
        ("Receita", "Aulas avulsas recebidas", "1450.00", 10),
        ("Despesa", "Ração", "3600.00", 3),
        ("Despesa", "Feno e maravalha", "1200.00", 4),
        ("Despesa", "Veterinário", "850.00", 12),
        ("Despesa", "Ferrageamento", "600.00", 15),
        ("Despesa", "Energia e água", "780.00", 20),
        ("Despesa", "Salário do tratador", "2800.00", 25),
    ]
    for tipo, desc, valor, dia in lancamentos:
        d = mes + timedelta(days=dia - 1)
        if d <= hoje:
            MovimentacaoFinanceira.objects.create(
                empresa=emp, descricao=desc, valor=Decimal(valor), tipo=tipo, data=d)

# 5. Planos, distribuídos entre os atletas
pl1 = Plano.objects.create(empresa=emp, nome="2x por semana", valor_mensal=Decimal("1200.00"), descricao="Demo")
pl2 = Plano.objects.create(empresa=emp, nome="Diário", valor_mensal=Decimal("2400.00"), descricao="Demo")
for n, aluno in enumerate(Aluno.objects.filter(empresa=emp).order_by("id")):
    aluno.plano = pl1 if n % 2 == 0 else pl2
    aluno.save(update_fields=["plano"])

# 6. Documentos com validades variadas (vencido, a vencer e em dia)
for i, cav in enumerate(cavalos[:6]):
    DocumentoCavalo.objects.create(cavalo=cav, titulo="GTA", tipo="GTA",
                                   data_validade=hoje + timedelta(days=200))
    DocumentoCavalo.objects.create(cavalo=cav, titulo="Atestado de vacinação", tipo="VACINA",
                                   data_validade=hoje + timedelta(days=[-30, 15, 90][i % 3]))
DocumentoCavalo.objects.create(cavalo=cavalos[0], titulo="Exame Mormo/Anemia", tipo="EXAME",
                               data_validade=hoje - timedelta(days=60))

# 7. Ocorrências de saúde
for (titulo, dias), cav in zip([("Cólica leve", 45), ("Casco rachado", 20),
                                ("Ferimento no pescoço", 6)], cavalos[:3]):
    RegistroOcorrencia.objects.create(
        cavalo=cav, data=timezone.now() - timedelta(days=dias), titulo=titulo,
        descricao="Registro de teste.", veterinario="Dr. Demo")

# 8. Agenda de eventos do cavalo (veterinário, ferrageamento, descanso)
for cav, tipo, dias in [(cavalos[0], "VETERINARIO", -12), (cavalos[1], "FERRAGEAMENTO", 3),
                        (cavalos[2], "DESCANSO", 5), (cavalos[3], "VETERINARIO", 9)]:
    ini = aware(hoje + timedelta(days=dias), 8)
    EventoAgendaCavalo.objects.create(
        cavalo=cav, tipo=tipo, data_inicio=ini, data_fim=ini + timedelta(hours=2),
        observacoes="Evento demo")

print(f"Cavalos: {Cavalo.objects.filter(empresa=emp).count()} | "
      f"Aulas: {Aula.objects.filter(empresa=emp).count()} | "
      f"Lotes: {LoteEstoque.objects.filter(item__empresa=emp).count()} | "
      f"Mov. estoque: {MovimentacaoEstoque.objects.filter(empresa=emp).count()} | "
      f"Mov. financeiro: {MovimentacaoFinanceira.objects.filter(empresa=emp).count()} | "
      f"Planos: {Plano.objects.filter(empresa=emp).count()} | "
      f"Documentos: {DocumentoCavalo.objects.filter(cavalo__empresa=emp).count()} | "
      f"Ocorrências: {RegistroOcorrencia.objects.filter(cavalo__empresa=emp).count()} | "
      f"Eventos: {EventoAgendaCavalo.objects.filter(cavalo__empresa=emp).count()}")
