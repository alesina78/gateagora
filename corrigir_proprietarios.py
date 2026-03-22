import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from gateagora.models import Aluno, Cavalo

# Mapeamento: nome do aluno -> lista de cavalos que lhe pertencem
vinculos = {
    'Beatriz Mello':   ['Farol', 'Trovão', 'Trueno'],
    'Cláudia Teles':   ['Capitão', 'Flecha', 'Hércules'],
    'Ivan Rocha':      ['Maestoso', 'Naja', 'Xamã'],
    'Marina Farias':   ['Estrela', 'Relâmpago', 'Sírius'],
    'Rogério Pacheco': ['Castor', 'Pérola', 'Ventania'],
}

erros = []
atualizados = 0

for nome_aluno, nomes_cavalos in vinculos.items():
    try:
        aluno = Aluno.objects.get(nome=nome_aluno)
    except Aluno.DoesNotExist:
        erros.append(f"ALUNO NAO ENCONTRADO: {nome_aluno}")
        continue

    for nome_cavalo in nomes_cavalos:
        try:
            cavalo = Cavalo.objects.get(nome=nome_cavalo)
            cavalo.proprietario = aluno
            cavalo.categoria = 'HOTELARIA'
            cavalo.mensalidade_baia = 1200.00
            cavalo.save(update_fields=['proprietario', 'categoria', 'mensalidade_baia'])
            print(f"OK: {cavalo.nome} -> {aluno.nome}")
            atualizados += 1
        except Cavalo.DoesNotExist:
            erros.append(f"CAVALO NAO ENCONTRADO: {nome_cavalo}")

print()
print(f"Total atualizados: {atualizados}")
if erros:
    print("ERROS:")
    for e in erros:
        print(f"  {e}")
else:
    print("Nenhum erro!")
