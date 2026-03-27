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
    Aula, ItemEstoque, DocumentoCavalo, RegistroOcorrencia, ConfigPrazoManejo
)

def run():
    print("🚀 Iniciando Carga Total de Dados: Hípica Paraíso RS...")

    # 1. GARANTE A EMPRESA
    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    # 2. CONFIGURAÇÃO DE EQUIPE (USUÁRIOS E PERFIS)
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

    # 3. ESTRUTURA FÍSICA (BAIAS E PIQUETES)
    piquete_principal, _ = Piquete.objects.get_or_create(
        nome="Piquete Principal", empresa=hprs, defaults={'capacidade': 50}
    )
    # Correção: O campo no seu model é 'numero', não 'nome'
    for i in range(1, 33):
        Baia.objects.get_or_create(numero=str(i), empresa=hprs)
    print("✅ Estrutura física (32 Baias) criada.")

    # 4. ALUNOS E PROPRIETÁRIOS (Unificados)
    # Incluindo as donas informadas como alunas para permitir vínculo
    nomes_alunos = [
        "Luisa Giordano", "Alice", "Julia", "Julia Charlote", "Joana", "Pietra", 
        "Laura", "Marcela", "Juliana Bailarina", "Sofi", "Sandra", "Glênio", 
        "Miguel", "Alessandro", "Suzana", "Luiza Squeff", "Carlos Behr", 
        "Lisiana", "Liane", "Cecília", "Camila", "Luciana", "Maria Hemília", "Marcelo"
    ]
    
    alunos_lista = []
    for nome in nomes_alunos:
        al, _ = Aluno.objects.get_or_create(
            nome=nome, 
            empresa=hprs, 
            defaults={'telefone': "+5551991387872"}
        )
        alunos_lista.append(al)
    
    aluno_haras, _ = Aluno.objects.get_or_create(
        nome="Haras Paraíso RS", empresa=hprs, defaults={'telefone': "+5551991387872"}
    )
    print("✅ Lista de Alunos/Dono processada.")

    # 5. CADASTRO DE CAVALOS (CONFORME REGRAS TÉCNICAS)
    # (Nome, Idade, Usa Ferradura, Dono, Obs Médica, Dorme, Fica, Treino)
    cavalos_dados = [
        ("Galileu HPRD", 6, False, "Haras Paraíso RS", "Dores na pata", "PIQUETE", "PIQUETE", "PARADO"),
        ("Baruk", 8, True, "Cecília", "Muito magro, vacinas em dia", "BAIA", "PIQUETE", "PARADO"),
        ("Jade", 12, True, "Camila", "Sem dores, em dia", "BAIA", "PIQUETE", "PARADO"),
        ("Soneto", 8, True, "Luciana", "Recuperando de cirurgia", "BAIA", "PIQUETE", "PARADO"),
        ("Zenda", 8, True, "Camila", "Dores na paleta", "BAIA", "PIQUETE", "PARADO"),
        ("Catita", 19, True, "Maria Hemília", "Sem obs médicas", "BAIA", "PIQUETE", "PARADO"),
        ("Handover", 9, True, "Camila", "Manca e aerofágico", "BAIA", "PIQUETE", "PARADO"),
        ("Charlote", 9, False, "Júlia", "Sem obs médicas", "BAIA", "PIQUETE", "PARADO"),
        ("Pegaus", 6, True, "Marcelo", "Sem obs médicas", "BAIA", "PIQUETE", "PARADO"),
        ("Pé de Pano HPRD", 29, False, "Haras Paraíso RS", "Baixa visão", "BAIA", "PIQUETE", "PARADO"),
        ("Bailarina", 8, True, "Júlia", "Sem obs médicas", "BAIA", "BAIA", "NORMAL"),
        ("Havaiano", 12, True, "Cecília", "Muito magro", "BAIA", "PIQUETE", "LEVE"),
        ("Gringa", 8, False, "Marcela", "Sem obs médicas", "BAIA", "PIQUETE", "NORMAL"),
        ("Gatiada HPRD", 36, False, "Haras Paraíso RS", "Velha, pouca visão", "BAIA", "BAIA", "PARADO"),
        ("Fina Flor HPRD", 23, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Braína HPRD", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Danuza HPRD", 12, False, "Haras Paraíso RS", "GTA atrasado, vacina vencida", "BAIA", "BAIA", "PARADO"),
        ("Amiga HPRD", 12, False, "Haras Paraíso RS", "Obs na respiração", "BAIA", "BAIA", "PARADO"),
        ("Bordada HPRD", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Aromah HPRD", 11, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Fênix HPRD", 10, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Badalada HPRD", 16, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Jobin HPRD", 5, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Zeus", 7, False, "Luísa", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Asterix HPRD", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
        ("Duque HPRD", 15, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
        ("Órion HPRD", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
        # Cavalos extras para completar 32
        ("Trovão HPRD", 10, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Relâmpago HPRD", 12, True, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Zorro", 14, True, "Alice", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Diamante", 9, True, "Joana", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Pérola", 7, False, "Pietra", "Sem obs", "BAIA", "BAIA", "NORMAL"),
    ]

    cavalos_criados = []
    hoje = timezone.localdate()

    for i, (nome, idade, ferradura, prop_nome, obs, dorme, local, treino) in enumerate(cavalos_dados):
        dono, _ = Aluno.objects.get_or_create(nome=prop_nome, empresa=hprs, defaults={'telefone': "+5551991387872"})
        
        # Tenta vincular uma baia se o cavalo dorme em baia
        baia_vinc = None
        if dorme == "BAIA":
            baia_vinc = Baia.objects.filter(empresa=hprs, numero=str(i+1)).first()

        cav, _ = Cavalo.objects.update_or_create(
            nome=nome, empresa=hprs,
            defaults={
                'categoria': 'PROPRIO' if "HPRD" in nome else 'HOTELARIA',
                'proprietario': dono,
                'idade': idade,
                'usa_ferradura': 'SIM' if ferradura else 'NAO',
                'observacoes_medicas': obs,
                'onde_dorme': dorme,
                'baia': baia_vinc,
                'piquete': piquete_principal if local == "PIQUETE" else None,
                'ultima_vacina': hoje - timedelta(days=random.randint(20, 180)),
                'ultimo_vermifugo': hoje - timedelta(days=random.randint(10, 60)),
            }
        )
        cavalos_criados.append(cav)

        # 6. DOCUMENTOS (Regra: Danuza Vencido, outros em dia)
        status_doc = 'VENCIDO' if "Danuza" in nome else 'EM_DIA'
        vencimento = hoje - timedelta(days=15) if status_doc == 'VENCIDO' else hoje + timedelta(days=90)
        DocumentoCavalo.objects.update_or_create(
            cavalo=cav, tipo='GTA', 
            defaults={'status': status_doc, 'data_vencimento': vencimento}
        )

    print(f"✅ {len(cavalos_criados)} Cavalos cadastrados e Documentos gerados.")

    # 7. ESTOQUE CRÍTICO
    estoque_itens = [
        ("Feno", 2, 10), ("Ração Algibeira", 3, 15), 
        ("Serragem", 1, 5), ("Alfafa", 2, 8)
    ]
    for nome_item, atual, min_alerta in estoque_itens:
        ItemEstoque.objects.update_or_create(
            nome=nome_item, empresa=hprs, 
            defaults={'quantidade_atual': atual, 'alerta_minimo': min_alerta, 'unidade_medida': 'FARDO'}
        )
    print("✅ Estoque crítico configurado.")

    # 8. HISTÓRICO DE AULAS (Ajustado para o período solicitado)
    print("⏳ Gerando histórico de aulas (Nov/25 a Abr/26)...")
    data_ini = date(2025, 11, 1)
    data_fim = date(2026, 4, 30)
    delta = (data_fim - data_ini).days

    for i in range(delta + 1):
        dia = data_ini + timedelta(days=i)
        if dia.weekday() == 6: continue # Sem aulas domingo

        for _ in range(2): # 2 aulas por dia para volume de dados
            cav = random.choice(cavalos_criados)
            alu = random.choice(alunos_lista)
            prof = random.choice(professores)
            dt_hora = timezone.make_aware(timezone.datetime.combine(dia, timezone.datetime.min.time().replace(hour=random.choice([9, 14, 16]))))
            
            Aula.objects.create(
                empresa=hprs, cavalo=cav, aluno=alu, professor=prof,
                data=dia, hora_inicio=dt_hora, status='REALIZADA'
            )

    print("✨ SUCESSO TOTAL: HPRD - Haras Paraíso RS operando com todos os dados!")

if __name__ == "__main__":
    run()