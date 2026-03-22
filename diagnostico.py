from gateagora.models import Aluno, Cavalo, Aula, MovimentacaoFinanceira
from django.utils import timezone

hoje = timezone.localdate()

print("=" * 60)
print("ALUNOS / CAVALOS / MENSALIDADES")
print("=" * 60)
for a in Aluno.objects.all():
    cavalos = Cavalo.objects.filter(proprietario=a)
    print(f"{a.nome} | valor_aula={a.valor_aula}")
    for c in cavalos:
        print(f"  -> {c.nome} | mensalidade_baia={c.mensalidade_baia}")

print()
print("=" * 60)
print("AULAS - MARCO 2026")
print("=" * 60)
aulas = Aula.objects.filter(data_hora__year=hoje.year, data_hora__month=hoje.month)
print(f"Total: {aulas.count()} | Concluidas: {aulas.filter(concluida=True).count()}")
for au in aulas[:10]:
    print(f"  {au.data_hora.date()} | {au.aluno.nome} | concluida={au.concluida}")

print()
print("=" * 60)
print("FINANCEIRO - ULTIMAS 10 MOVIMENTACOES")
print("=" * 60)
for m in MovimentacaoFinanceira.objects.all().order_by('-data')[:10]:
    print(f"{m.data} | {m.tipo} | R${m.valor} | {m.descricao[:40]}")
