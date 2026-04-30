# Rode com: python corrigir_encoding.py
# Na pasta C:\_GestaoHipica\GATEAGORA

import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from gateagora.models import Aluno, Cavalo, ItemEstoque, Empresa

# ── Correções de Alunos ───────────────────────────────────────────────────────
alunos = {
    'Cecí­lia Fontana':       'Cecília Fontana',
    'CÃ­ntia Hartmann':       'Cíntia Hartmann',
    'DÃ©bora Lima':           'Débora Lima',
    'FÃ¡bio Zanella':         'Fábio Zanella',
    'Haras Paraí­so RS':      'Haras Paraíso RS',
    'HÃ­pica Cavalos do Sul': 'Hípica Cavalos do Sul',
    'Luí­sa Giordano':        'Luísa Giordano',
    'Maria HemÃ­lia Costa':   'Maria Hemília Costa',
    'NatÃ¡lia Costa':         'Natália Costa',
}

for errado, correto in alunos.items():
    n = Aluno.objects.filter(nome=errado).update(nome=correto)
    print(f"Aluno: {'OK' if n else 'não encontrado'} — {correto}")

# ── Correções de Cavalos ──────────────────────────────────────────────────────
cavalos = {
    'MÃ­stica':    'Mística',
    'RelÃ¢mpago':  'Relâmpago',
    'Órion HPRD':  'Órion HPRD',  # já correto, só confirma
}

for errado, correto in cavalos.items():
    n = Cavalo.objects.filter(nome=errado).update(nome=correto)
    print(f"Cavalo: {'OK' if n else 'não encontrado'} — {correto}")

# ── Correções de Estoque ──────────────────────────────────────────────────────
estoque = {
    'VermÃ­fugo Equalan':      'Vermífugo Equalan',
    'Seringas DescartÃ¡veis':  'Seringas Descartáveis',
    'RaÃ§Ã£o Premium 25kg':    'Ração Premium 25kg',
    'Ã"leo de Milho':          'Óleo de Milho',
    'VermÃ­fugo Panacur':      'Vermífugo Panacur',
    'AgulhasDescartÃ¡veis':    'Agulhas Descartáveis',
    'Agulhas DescartÃ¡veis':   'Agulhas Descartáveis',
    'Ã"leo de Coco Equino':    'Óleo de Coco Equino',
}

for errado, correto in estoque.items():
    n = ItemEstoque.objects.filter(nome=errado).update(nome=correto)
    print(f"Estoque: {'OK' if n else 'não encontrado'} — {correto}")

# ── Correções de Empresa ──────────────────────────────────────────────────────
empresas = {
    'HÃ­pica Cavalos do Sul': 'Hípica Cavalos do Sul',
    'Haras ParaÃ­so RS':      'Haras Paraíso RS',
}

for errado, correto in empresas.items():
    n = Empresa.objects.filter(nome=errado).update(nome=correto)
    print(f"Empresa: {'OK' if n else 'não encontrado'} — {correto}")

print("\nConcluído.")
