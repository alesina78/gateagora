# -*- coding: utf-8 -*-
import os
import django
import random
from decimal import Decimal
from datetime import datetime, date, timedelta
from django.utils import timezone

# Configuração do Ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, Piquete, 
    Aula, ItemEstoque, MovimentacaoFinanceira
)

def limpar_dados():
    print("Limpando base de dados antiga...")
    MovimentacaoFinanceira.objects.all().delete()
    Aula.objects.all().delete()
    ItemEstoque.objects.all().delete()
    Cavalo.objects.all().delete()
    Piquete.objects.all().delete()
    Baia.objects.all().delete()
    Aluno.objects.all().delete()
    Perfil.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()
    Empresa.objects.all().delete()

def criar_usuarios():
    print("Criando usuários e empresas...")
    
    # Empresa A
    e1 = Empresa.objects.create(nome="Haras Elite Prateada", slug="elite-prateada", cidade="Portão")
    u1 = User.objects.create_user(username="gestor_hipica1", email="gateagora@gmail.com", password="Teste123")
    Perfil.objects.create(user=u1, empresa=e1, cargo='Gestor')

    # Empresa B
    e2 = Empresa.objects.create(nome="Centro Hípico Aguiar", slug="hipico-aguiar", cidade="São Leopoldo")
    u2 = User.objects.create_user(username="admin4", email="gateagora@gmail.com", password="Gate$2024")
    Perfil.objects.create(user=u2, empresa=e2, cargo='Gestor')

    # Professor para aulas
    prof = User.objects.create_user(username="professor_teste", password="Gate$2024")
    p_prof = Perfil.objects.create(user=prof, empresa=e1, cargo='Professor')

    return e1, e2, p_prof

def popular_empresa(empresa, professor, prefixo_nomes):
    print(f"Populando dados para: {empresa.nome}")
    
    # 1. Aluno "Hípica" para cavalos próprios
    aluno_hipica = Aluno.objects.create(
        empresa=empresa, nome=f"Gestão {empresa.nome}", 
        telefone="+5551991387872", ativo=True
    )

    # 2. Criar Baias e Piquetes
    baias = [Baia.objects.create(empresa=empresa, numero=str(i), status='Livre') for i in range(1, 33)]
    piquete = Piquete.objects.create(empresa=empresa, nome="Piquete Leste", capacidade=10)

    # 3. Criar Alunos (15 no total, 5 são proprietários)
    nomes_alunos = ["Ricardo", "Beatriz", "Carlos", "Fernanda", "Gabriel", "Helena", "Igor", "Julia", "Lucas", "Mariana", "Nuno", "Olivia", "Paulo", "Quiteria", "Rafael"]
    alunos_objs = []
    for i, nome in enumerate(nomes_alunos):
        a = Aluno.objects.create(
            empresa=empresa, 
            nome=f"{nome} {prefixo_nomes}", 
            telefone="+5551991387872",
            valor_aula=Decimal("150.00")
        )
        alunos_objs.append(a)

    # 4. Criar Cavalos (32 totais: 17 Próprios, 15 Hotelaria)
    nomes_cavalos = ["Apolo", "Zéfiro", "Luna", "Trovão", "Fênix", "Diamante", "Pérola", "Eclipse", "Cometa", "Atena", "Baco", "Cigana", "Dante", "Estrela", "Faísca", "Garoa", "Hera", "Ícaro", "Jasmim", "Kaiser", "Lorde", "Mistério", "Netuno", "Orion", "Pégaso", "Quartzo", "Raio", "Sombra", "Titã", "Urano", "Vênus", "Zorro"]
    
    hoje = date.today()
    for i in range(32):
        is_proprio = i < 17
        dono = aluno_hipica if is_proprio else alunos_objs[i % 5] # Primeiros 5 alunos são os donos
        
        c = Cavalo.objects.create(
            empresa=empresa,
            nome=nomes_cavalos[i],
            categoria='PROPRIO' if is_proprio else 'HOTELARIA',
            proprietario=dono,
            baia=baias[i],
            material_proprio=(i < 2), # 2 com material próprio
            mensalidade_baia=Decimal("1200.00") if not is_proprio else Decimal("0.00")
        )

        # Datas de Manejo específicas solicitadas
        if i == 0 or i == 1: # 2 com casqueio em 3 dias
            c.ultimo_casqueamento = hoje - timedelta(days=42) # Próximo será logo
        if i >= 2 and i <= 5: # 4 com vermifugação em 2 dias
            c.ultimo_vermifugo = hoje - timedelta(days=88)
        c.save()

    # 5. Financeiro (Nov/2025 a Mar/2026)
    data_inicio = date(2025, 11, 1)
    for i in range(150):
        data_mov = data_inicio + timedelta(days=i)
        if data_mov > date(2026, 3, 30): break
        
        # Receitas (Mensalidades no dia 5)
        if data_mov.day == 5:
            MovimentacaoFinanceira.objects.create(
                empresa=empresa, descricao="Mensalidades Hotelaria",
                valor=Decimal(random.randint(5000, 8000)), tipo='Receita', data=data_mov
            )
        # Despesas aleatórias
        if random.random() > 0.7:
            MovimentacaoFinanceira.objects.create(
                empresa=empresa, descricao="Compra de Feno/Ração",
                valor=Decimal(random.randint(1200, 3000)), tipo='Despesa', data=data_mov
            )

    # 6. Aulas (Segunda a Sábado)
    cavalos_aula = Cavalo.objects.filter(empresa=empresa)
    for i in range(120):
        data_aula = data_inicio + timedelta(days=i)
        if data_aula.weekday() == 6: continue # Sem domingo
        if data_aula > date(2026, 3, 30): break

        dt_hora = timezone.make_aware(datetime.combine(data_aula, datetime.min.time().replace(hour=random.randint(8, 17))))
        
        Aula.objects.create(
            empresa=empresa,
            aluno=random.choice(alunos_objs),
            cavalo=random.choice(cavalos_aula),
            instrutor=professor,
            data_hora=dt_hora,
            concluida=(data_aula < hoje)
        )

if __name__ == "__main__":
    limpar_dados()
    emp1, emp2, prof_e1 = criar_usuarios()
    popular_empresa(emp1, prof_e1, "Haras A")
    popular_empresa(emp2, prof_e1, "Haras B") # Usando mesmo prof para simplificar o seed
    print("\n[SUCESSO] Dados gerados de 01/11/2025 até 30/03/2026!")
    print("Logins disponíveis:")
    print("- admin4 / Gate$2024")
    print("- gestor_hipica1 / Teste123")