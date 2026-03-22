from gateagora.models import Aluno, Cavalo, Aula
from django.utils import timezone

hoje = timezone.localdate()
print(f"Hoje: {hoje} | Mes: {hoje.month}/{hoje.year}")
print()

# Aulas concluidas em marco
aulas_marco = Aula.objects.filter(
    concluida=True,
    data_hora__year=hoje.year,
    data_hora__month=hoje.month
)
print(f"Aulas concluidas em {hoje.month}/{hoje.year}: {aulas_marco.count()}")
for a in aulas_marco:
    print(f"  {a.data_hora.date()} | {a.aluno.nome} | valor_aula={a.aluno.valor_aula}")

print()
print("Alunos com hotelaria > 0:")
for a in Aluno.objects.all():
    cavalos = Cavalo.objects.filter(proprietario=a, mensalidade_baia__gt=0)
    if cavalos.exists():
        total = sum(c.mensalidade_baia for c in cavalos)
        print(f"  {a.nome} | hotelaria={total}")
