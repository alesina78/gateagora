# -*- coding: utf-8 -*-
import os
import django
import random
from decimal import Decimal
from datetime import timedelta, date
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo, 
    Aula, ItemEstoque, DocumentoCavalo, RegistroOcorrencia
)

def run():
    print("🚀 Iniciando Carga TOTAL de Dados: Hípica Paraíso RS...")

    # 1. GARANTE A EMPRESA
    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    # 2. CONFIGURAÇÃO DE EQUIPE
    def configurar_equipe(username, senha, cargo):
        u, created = User.objects.get_or_create(username=username)
        u.set_password(senha)
        u.is_staff = True
        u.is_active = True
        u.save()
        Perfil.objects.update_or_create(user=u, defaults={'empresa': hprs, 'cargo': cargo})
        return u

    professores = [
        configurar_equipe("Suzana", "Asterix", 'Gestor'),
        configurar_equipe("Dado", "Dado$Verde", 'Professor'),
        configurar_equipe("Alessandro", "Dado$Verde", 'Professor'),
        configurar_equipe("Luiza Squeff", "Dado$Verde", 'Professor')
    ]
    configurar_equipe("Rodrigo", "Dado$Verde", 'Tratador')
    configurar_equipe("Maurício", "Dado$Verde", 'Tratador')
    print("✅ Equipe e acessos configurados.")

    # 3. ESTRUTURA FÍSICA
    piquete_principal, _ = Piquete.objects.get_or_create(
        nome="Piquete Principal", empresa=hprs, defaults={'capacidade': 50}
    )
    for i in range(1, 33):
        Baia.objects.get_or_create(numero=str(i), empresa=hprs)
    print("✅ Estrutura física (32 Baias) criada.")

    # 4. ALUNOS E PROPRIETÁRIOS
    nomes_alunos = [
        "Luisa Giordano", "Alice", "Julia", "Julia Charlote", "Joana", "Pietra", 
        "Laura", "Marcela", "Juliana Bailarina", "Sofi", "Sandra", "Glênio", 
        "Miguel", "Alessandro", "Suzana", "Luiza Squeff", "Carlos Behr", 
        "Lisiana", "Liane", "Cecília", "Camila", "Luciana", "Maria Hemília", "Marcelo"
    ]
    
    alunos_lista = []
    for nome in nomes_alunos:
        al, _ = Aluno.objects.get_or_create(
            nome=nome, empresa=hprs, 
            defaults={'telefone': "+5551991387872"}
        )
        alunos_lista.append(al)
    
    aluno_haras, _ = Aluno.objects.get_or_create(
        nome="Haras Paraíso RS", empresa=hprs, defaults={'telefone': "+5551991387872"}
    )
    print("✅ Lista de Alunos/Dono processada.")

    # 5. CADASTRO INTEGRAL DE 32 CAVALOS
    # Formato: (Nome, Ferradura, Dono, Obs, Dorme, Local)
    # Nota: Removido campo 'idade' e 'observacoes_medicas' (ajustado para 'observacoes')
    cavalos_dados = [
        ("Galileu HPRD", False, "Haras Paraíso RS", "Dores na pata", "PIQUETE", "PIQUETE"),
        ("Baruk", True, "Cecília", "Muito magro, vacinas em dia", "BAIA", "PIQUETE"),
        ("Jade", True, "Camila", "Sem dores, em dia", "BAIA", "PIQUETE"),
        ("Soneto", True, "Luciana", "Recuperando de cirurgia", "BAIA", "PIQUETE"),
        ("Zenda", True, "Camila", "Dores na paleta", "BAIA", "PIQUETE"),
        ("Catita", True, "Maria Hemília", "Sem obs médicas", "BAIA", "PIQUETE"),
        ("Handover", True, "Camila", "Manca e aerofágico", "BAIA", "PIQUETE"),
        ("Charlote", False, "Julia", "Sem obs médicas", "BAIA", "PIQUETE"),
        ("Pegaus", True, "Marcelo", "Sem obs médicas", "BAIA", "PIQUETE"),
        ("Pé de Pano HPRD", False, "Haras Paraíso RS", "Baixa visão", "BAIA", "PIQUETE"),
        ("Bailarina", True, "Julia", "Sem obs médicas", "BAIA", "BAIA"),
        ("Havaiano", True, "Cecília", "Muito magro", "BAIA", "PIQUETE"),
        ("Gringa", False, "Marcela", "Sem obs médicas", "BAIA", "PIQUETE"),
        ("Gatiada HPRD", False, "Haras Paraíso RS", "Velha, pouca visão", "BAIA", "BAIA"),
        ("Fina Flor HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Braína HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Danuza HPRD", False, "Haras Paraíso RS", "GTA atrasado, vacina vencida", "BAIA", "BAIA"),
        ("Amiga HPRD", False, "Haras Paraíso RS", "Obs na respiração", "BAIA", "BAIA"),
        ("Bordada HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Aromah HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Fênix HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Badalada HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Jobin HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Zeus", False, "Luisa Giordano", "Sem obs", "BAIA", "BAIA"),
        ("Asterix HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Duque HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Órion HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Trovão HPRD", False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Relâmpago HPRD", True, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Zorro", True, "Alice", "Sem obs", "BAIA", "BAIA"),
        ("Diamante", True, "Joana", "Sem obs", "BAIA", "BAIA"),
        ("Pérola", False, "Pietra", "Sem obs", "BAIA", "BAIA"),
    ]

    cavalos_criados = []
    hoje = timezone.localdate()

    for i, (nome, ferradura, prop_nome, obs, dorme, local) in enumerate(cavalos_dados):
        dono, _ = Aluno.objects.get_or_create(nome=prop_nome, empresa=hprs)
        
        baia_vinc = None
        if dorme == "BAIA":
            baia_vinc = Baia.objects.filter(empresa=hprs, numero=str(i+1)).first()

        cav, _ = Cavalo.objects.update_or_create(
            nome=nome, empresa=hprs,
            defaults={
                'categoria': 'PROPRIO' if "HPRD" in nome else 'HOTELARIA',
                'proprietario': dono,
                'usa_ferradura': 'SIM' if ferradura else 'NAO',
                'observacoes': obs,
                'onde_dorme': dorme,
                'baia': baia_vinc,
                'piquete': piquete_principal if local == "PIQUETE" else None,
                'status': 'NORMAL',
                'ultima_vacina': hoje - timedelta(days=random.randint(20, 180)),
                'ultimo_vermifugo': hoje - timedelta(days=random.randint(10, 60)),
            }
        )
        cavalos_criados.append(cav)

        # 6. DOCUMENTOS
        status_doc = 'VENCIDO' if "Danuza" in nome else 'EM_DIA'
        vencimento = hoje - timedelta(days=15) if status_doc == 'VENCIDO' else hoje + timedelta(days=90)
        DocumentoCavalo.objects.update_or_create(
            cavalo=cav, tipo='GTA', 
            defaults={'status': status_doc, 'data_vencimento': vencimento}
        )

    print(f"✅ {len(cavalos_criados)} Cavalos cadastrados e Documentos gerados.")

    # 7. ESTOQUE CRÍTICO
    # Correção: O campo no model é 'unidade', não 'unidade_medida'
    estoque_itens = [
        ("Feno", 2, 10), ("Ração Algibeira", 3, 15), 
        ("Serragem", 1, 5), ("Alfafa", 2, 8)
    ]
    for nome_item, atual, min_alerta in estoque_itens:
        ItemEstoque.objects.update_or_create(
            nome=nome_item, empresa=hprs, 
            defaults={'quantidade_atual': atual, 'alerta_minimo': min_alerta, 'unidade': 'FARDO'}
        )
    print("✅ Estoque crítico configurado.")

    # 8. HISTÓRICO DE AULAS (Nov/25 a Abr/26)
    print("⏳ Gerando histórico de aulas (Nov/25 a Abr/26)...")
    data_ini = date(2025, 11, 1)
    data_fim = date(2026, 4, 30)
    delta = (data_fim - data_ini).days

    for i in range(delta + 1):
        dia = data_ini + timedelta(days=i)
        if dia.weekday() == 6: continue 

        for _ in range(2): 
            cav = random.choice(cavalos_criados)
            alu = random.choice(alunos_lista)
            prof = random.choice(professores)
            dt_hora = timezone.make_aware(timezone.datetime.combine(dia, timezone.datetime.min.time().replace(hour=random.choice([9, 14, 16]))))
            
            Aula.objects.create(
                empresa=hprs, cavalo=cav, aluno=alu, professor=prof,
                data=dia, hora_inicio=dt_hora, status='REALIZADA'
            )

    print("✨ SUCESSO TOTAL: Sistema HPRD populado com dados reais e históricos!")

if __name__ == "__main__":
    run()