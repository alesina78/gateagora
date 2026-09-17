import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Configuração do Ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from gateagora.models import Aluno, Cavalo, Baia, Piquete, Aula, MovimentacaoFinanceira, ItemEstoque

def gerar_operacao_completa():
    print("--- 🐎 Iniciando Carga Gate 4 (Versão Realista Enterprise) ---")

    # --- PASSO ZERO: LIMPEZA TOTAL ---
    Aula.objects.all().delete()
    Cavalo.objects.all().delete()
    Baia.objects.all().delete()
    Piquete.objects.all().delete()
    Aluno.objects.all().delete()
    MovimentacaoFinanceira.objects.all().delete()
    ItemEstoque.objects.all().delete()

    # 1. CRIAR SÓCIOS/CLIENTES (20) - Nomes mais realistas
    socios = []
    nomes_socios = [
        "Ricardo Almeida", "Beatriz Fontes", "Carlos Eduardo", "Fernanda Lima", "Gustavo Prata",
        "Helena Silveira", "João Pedro", "Karina Schmidt", "Lucas Moura", "Mariana Costa",
        "Sócio Investidor 01", "Sócio Investidor 02", "Sócio Investidor 03", "Arthur Aguiar", "Camila Telles",
        "Eduardo Paes", "Fabiana Melo", "Gabriel Rocha", "Henrique Viana", "Isabela Neves"
    ]
    
    for i in range(20):
        s = Aluno.objects.create(
            nome=nomes_socios[i],
            telefone=f"55119{random.randint(7000,9999)}{random.randint(1000,9999)}",
            valor_aula=180.00, # Valor atualizado para o nível do haras
            ativo=True
        )
        socios.append(s)

    # 2. CRIAR ESTRUTURA FÍSICA (12 Baias e 12 Piquetes)
    baias = [Baia.objects.create(numero=f"B{i:02d}", status='Livre') for i in range(1, 13)]
    piquetes = [Piquete.objects.create(nome=f"Piquete {i:02d}", capacidade=3, status='Livre') for i in range(1, 13)]

    # 3. CRIAR CAVALOS (30 no total) - Nomes de linhagem e esportivos
    nomes_cavalos = [
        "Zimbro do Passo", "Diamante Negro", "Baronesa Real", "Trovão Azul", "Estrela da Guia", 
        "Hércules da Gate", "Luna de Ouro", "Falcão Real", "Dama de Ferro", "Albatroz", 
        "Soberano", "Safira", "Vento Norte", "Cigana", "Titã", 
        "Fênix", "Jade", "Cometa", "Alegria", "Guerreiro", 
        "Barão", "Pégaso", "Íris", "Netuno", "Vênus", 
        "Cronos", "Gaia", "Shadow", "Relâmpago", "Ares"
    ]
    
    hoje_data = timezone.now().date()

    for i in range(30):
        # 15 Escola (PROPRIO) / 15 Hotelaria (HOTELARIA)
        tipo_cat = 'PROPRIO' if i < 15 else 'HOTELARIA'
        
        # Simulando Ferrageamento (alguns precisam estar vencidos > 40 dias)
        dias_ultimo_ferrageamento = random.randint(10, 55) # Gera alguns alertas
        ferrageamento_data = hoje_data - timedelta(days=dias_ultimo_ferrageamento)
        
        # LÓGICA DE ALOCAÇÃO: 11 em Baias (DEIXA A B12 LIVRE), 19 em Piquetes
        if i < 11:
            onde_dorme = 'BAIA'
            baia_atual = baias[i]
            piquete_atual = None
            baia_atual.status = 'Ocupada'
            baia_atual.save()
        else:
            onde_dorme = 'PIQUETE'
            baia_atual = None
            piquete_atual = piquetes[i % 12]
            piquete_atual.status = 'Ocupado'
            piquete_atual.save()

        Cavalo.objects.create(
            nome=nomes_cavalos[i],
            categoria=tipo_cat,
            # Se passou de 40 dias, status vira 'Alerta'
            status_saude='Saudável' if dias_ultimo_ferrageamento <= 40 else 'Alerta',
            onde_dorme=onde_dorme,
            baia=baia_atual,
            piquete=piquete_atual,
            proprietario=random.choice(socios),
            ultima_vacina=hoje_data - timedelta(days=random.randint(20, 200)),
            ultimo_ferrageamento=ferrageamento_data,
            racao="2kg Guabi Equi-S Manhã / 2kg Noite",
            alfafa="1kg Alfafa Premium Tarde",
            feno="Coast Cross à vontade",
            pasto="Piquete Período Manhã",
            mensalidade_baia=2200.00 if tipo_cat == 'HOTELARIA' else 0,
            medicamentos_e_remedios="Suplemento Organnact" if i % 5 == 0 else "",
        )

    # 4. FINANCEIRO (Histórico de 6 meses)
    for m in range(6, -1, -1):
        data_m = hoje_data - timedelta(days=m*30)
        MovimentacaoFinanceira.objects.create(
            tipo='Receita',
            valor=random.uniform(25000, 35000),
            descricao=f"Receitas Totais - {data_m.strftime('%m/%Y')}"
        )
        MovimentacaoFinanceira.objects.create(
            tipo='Despesa',
            valor=random.uniform(12000, 18000),
            descricao=f"Despesas Operacionais - {data_m.strftime('%m/%Y')}"
        )

    # 5. AGENDA (Próximos dias)
    cavalos_escola = Cavalo.objects.filter(categoria='PROPRIO')
    for d in range(0, 3): 
        data_a = timezone.now() + timedelta(days=d)
        for _ in range(random.randint(4, 7)):
            tipo_aula = random.choice(['NORMAL', 'NORMAL', 'RECUPERAR'])
            Aula.objects.create(
                aluno=random.choice(socios),
                cavalo=random.choice(cavalos_escola),
                data_hora=data_a.replace(hour=random.randint(8, 17), minute=0, second=0, microsecond=0),
                tipo=tipo_aula,
                concluida=False
            )

    # 6. ESTOQUE (Itens reais de mercado equino)
    ItemEstoque.objects.create(nome="Ração Guabi Equi-S (Sacos)", quantidade_atual=8, alerta_minimo=15) # CRÍTICO
    ItemEstoque.objects.create(nome="Feno Coast Cross (Fardos)", quantidade_atual=60, alerta_minimo=20)  # OK
    ItemEstoque.objects.create(nome="Alfafa Premium (Fardos)", quantidade_atual=12, alerta_minimo=10)   # OK (Perto)
    ItemEstoque.objects.create(nome="Maravalha/Serragem (Sacos)", quantidade_atual=4, alerta_minimo=10) # CRÍTICO
    ItemEstoque.objects.create(nome="Suplemento Muscular (Potes)", quantidade_atual=5, alerta_minimo=2) # OK

    print(f"--- ✅ Sucesso! Operação Gate 4 Carregada ---")
    print(f"Sistemas: 11 Baias Ocupadas | Baia B12 LIVRE para novos clientes")
    print(f"Financeiro: Receitas vs Despesas simuladas para gráficos")
    print(f"Manejo: Alunos agora são Sócios e cavalos possuem dieta de alta performance")

if __name__ == '__main__':
    gerar_operacao_completa()