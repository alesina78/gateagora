# -*- coding: utf-8 -*-
import os
import django
import random
from datetime import date, timedelta
from decimal import Decimal

# 1. Configuração do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from gateagora.models import (
    Empresa, Perfil, Aluno, Cavalo, Baia, 
    MovimentacaoFinanceira, DocumentoCavalo, Aula
)

def limpar_dados(empresa):
    """Centraliza a limpeza de dados para evitar resquícios que sujam o gráfico."""
    Aula.objects.filter(empresa=empresa).delete()
    DocumentoCavalo.objects.filter(cavalo__empresa=empresa).delete()
    MovimentacaoFinanceira.objects.filter(empresa=empresa).delete()
    Cavalo.objects.filter(empresa=empresa).delete()
    Baia.objects.filter(empresa=empresa).delete()

def criar_usuarios(empresa):
    usuarios = [
        ('Admin', 'gateagora@gmail.com', 'Gate$2024'),
        ('admin4', 'gateagora@gmail.com', 'Gate$2024'),
        ('alessandro_admin', 'gateagora@gmail.com', 'Gate2024'),
        ('gestor_hipica1', 'gateagora@gmail.com', 'Teste123')
    ]
    for username, email, password in usuarios:
        if not User.objects.filter(username=username).exists():
            u = User.objects.create_superuser(username, email, password)
            Perfil.objects.get_or_create(user=u, defaults={'empresa': empresa, 'cargo': 'Dono'})

def popular_empresa(nome_empresa, slug_empresa):
    print(f"--- Populando: {nome_empresa} ---")
    
    empresa, _ = Empresa.objects.get_or_create(
        nome=nome_empresa, 
        defaults={'slug': slug_empresa, 'cidade': 'Portão', 'cnpj': '00.000.000/0001-00'}
    )
    
    limpar_dados(empresa)
    criar_usuarios(empresa)

    # 1. ALUNOS (15 total)
    # Criando a "Sede" como Aluno para ser dona dos cavalos próprios
    sede_dona = Aluno.objects.create(nome=f"Sede {nome_empresa}", empresa=empresa, telefone="+5551991387872", ativo=True)
    
    alunos_lista = []
    nomes_ficticios = ["Ricardo", "Beatriz", "Carlos", "Daniela", "Eduardo", "Fernanda", "Gabriel", "Helena", "Igor", "Julia", "Kevin", "Larissa", "Murilo", "Natália", "Otávio"]
    
    for i, nome in enumerate(nomes_ficticios):
        aluno = Aluno.objects.create(
            nome=f"{nome} Oliveira", 
            empresa=empresa, 
            telefone="+5551991387872", 
            ativo=True, 
            valor_aula=Decimal('150.00')
        )
        alunos_lista.append(aluno)

    # 2. BAIAS E CAVALOS (32 total: 17 Próprios, 15 Hotelaria)
    nomes_cavalos = ["Apolo", "Zéfiro", "Luna", "Relâmpago", "Pérola", "Trovão", "Sombra", "Dama", "Faraó", "Garoa", "Hércules", "Íris", "Júpiter", "Kaiser", "Lord", "Maestro", "Nobre", "Ouro", "Pégaso", "Quartzo", "Radar", "Safira", "Titan", "Urano", "Vênus", "Wind", "Xerife", "Yanka", "Zorro", "Alteza", "Barão", "Cometa"]
    
    baias = [Baia.objects.create(numero=str(i), empresa=empresa, status='Livre') for i in range(1, 45)]
    cavalos_obj = []

    for i in range(32):
        is_proprio = (i < 17)
        dono = sede_dona if is_proprio else alunos_lista[i % 5] # 5 primeiros alunos são proprietários
        
        cavalo = Cavalo.objects.create(
            nome=nomes_cavalos[i],
            empresa=empresa,
            proprietario=dono,
            categoria="Próprio" if is_proprio else "Hotelaria",
            baia=baias[i],
            mensalidade_baia=Decimal('1200.00') if not is_proprio else Decimal('0.00')
        )
        baias[i].status = 'Ocupada'
        baias[i].save()
        cavalos_obj.append(cavalo)

    # 3. SAÚDE (Alertas)
    hoje = date(2026, 3, 4)
    for c in cavalos_obj[:2]: # 2 Casqueios em 3 dias
        DocumentoCavalo.objects.create(titulo="Casqueio", cavalo=c, data_validade=hoje + timedelta(days=3))
    for c in cavalos_obj[2:6]: # 4 Vermifugação em 2 dias
        DocumentoCavalo.objects.create(titulo="Vermífugo", cavalo=c, data_validade=hoje + timedelta(days=2))

    # 4. FINANCEIRO (01/11/2025 até 30/03/2026)
    curr = date(2025, 11, 1)
    fim = date(2026, 3, 30)
    
    while curr <= fim:
        # Receita Hotelaria dia 1
        if curr.day == 1:
            MovimentacaoFinanceira.objects.create(
                data=curr, tipo="Receita", valor=Decimal('18000.00'),
                descricao="Mensalidades Hotelaria", empresa=empresa
            )
            # Despesa fixa dia 5
            MovimentacaoFinanceira.objects.create(
                data=curr + timedelta(days=4), tipo="Despesa", valor=Decimal(random.randint(6000, 9000)),
                descricao="Manutenção e Ração", empresa=empresa
            )

        # Aulas Sábados (Sem domingos)
        if curr.weekday() == 5:
            MovimentacaoFinanceira.objects.create(
                data=curr, tipo="Receita", valor=Decimal(random.randint(1500, 3500)),
                descricao="Aulas de Equitação", empresa=empresa
            )
        curr += timedelta(days=1)

    # 5. AULAS (Agenda)
    # Apenas para o dia atual, respeitando Timezone consciente
    agora = timezone.now()
    for i in range(5):
        Aula.objects.create(
            data_hora=timezone.make_aware(timezone.datetime(2026, 3, 4, 8 + i, 0)),
            aluno=random.choice(alunos_lista),
            cavalo=random.choice(cavalos_obj),
            tipo="Prática", empresa=empresa
        )

def executar():
    popular_empresa("Hípica Paraíso RS", "hipica-paraiso")
    popular_empresa("Haras Recanto", "haras-recanto")
    print("--- PROCESSO CONCLUÍDO COM SUCESSO ---")

if __name__ == "__main__":
    executar()