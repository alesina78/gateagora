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
        nome="Piquete Principal", empresa=hprs, defaults={'capacidade': 30}
    )
    for i in range(1, 21):
        Baia.objects.get_or_create(nome=f"Baia {i}", empresa=hprs)
    print("✅ Estrutura física criada.")

    # 4. ALUNOS E PROPRIETÁRIOS
    aluno_haras, _ = Aluno.objects.get_or_create(
        nome="Haras Paraíso RS", empresa=hprs, defaults={'telefone': "+5551991387872"}
    )
    
    nomes_alunos = [
        "Luisa Giordano", "Alice", "Julia", "Julia Charlote", "Joana", "Pietra", 
        "Laura", "Marcela", "Juliana Bailarina", "Sofi", "Sandra", "Glênio", 
        "Miguel", "Carlos Behr", "Lisiana", "Liane"
    ]
    alunos_lista = []
    for nome in nomes_alunos:
        al, _ = Aluno.objects.get_or_create(nome=nome, empresa=hprs, defaults={'telefone': "+5551991387872"})
        alunos_lista.append(al)
    print("✅ Alunos e Proprietários cadastrados.")

    # 5. CADASTRO DE CAVALOS (CONFORME REGRAS TÉCNICAS)
    # Formato: (Nome, Idade, Ferradura, Dono, Obs, Local_Dorme, Local_Fica, Treino)
    cavalos_dados = [
        ("Galileu HPRS", 6, False, "Haras Paraíso RS", "Dores na pata", "PIQUETE", "PIQUETE", "PARADO"),
        ("Baruk", 8, True, "Cecília", "Muito magro", "BAIA", "PIQUETE", "PARADO"),
        ("Jade", 12, True, "Camila", "Sem dores", "BAIA", "PIQUETE", "PARADO"),
        ("Soneto", 8, True, "Luciana", "Recuperando cirurgia", "BAIA", "PIQUETE", "PARADO"),
        ("Zenda", 8, True, "Camila", "Dores na paleta", "BAIA", "PIQUETE", "PARADO"),
        ("Catita", 19, True, "Maria Hemília", "Sem obs", "BAIA", "PIQUETE", "PARADO"),
        ("Handover", 9, True, "Camila", "Manca e aerofágico", "BAIA", "PIQUETE", "PARADO"),
        ("Charlote", 9, False, "Júlia", "Sem obs", "BAIA", "PIQUETE", "PARADO"),
        ("Pegaus", 6, True, "Marcelo", "Sem obs", "BAIA", "PIQUETE", "PARADO"),
        ("Pé de Pano HPRS", 29, False, "Haras Paraíso RS", "Baixa visão", "BAIA", "PIQUETE", "PARADO"),
        ("Bailarina", 8, True, "Júlia", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Havaiano", 12, True, "Cecília", "Muito magro", "BAIA", "PIQUETE", "LEVE"),
        ("Gringa", 8, False, "Marcela", "Sem obs", "BAIA", "PIQUETE", "NORMAL"),
        ("Gatiada HPRS", 36, False, "Haras Paraíso RS", "Muito velha e pouca visão", "BAIA", "BAIA", "PARADO"),
        ("Fina Flor HPRS", 23, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Braína HPRS", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Danuza HPRS", 12, False, "Haras Paraíso RS", "Documentos vencidos, GTA atrasado", "BAIA", "BAIA", "PARADO"),
        ("Amiga HPRS", 12, False, "Haras Paraíso RS", "Obs respiração", "BAIA", "BAIA", "PARADO"),
        ("Bordada HPRS", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Aromah HPRS", 11, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Fênix HPRS", 10, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Badalada HPRS", 16, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Jobin HPRS", 5, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "PARADO"),
        ("Zeus", 7, False, "Luísa", "Sem obs", "BAIA", "BAIA", "NORMAL"),
        ("Asterix HPRS", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
        ("Duque HPRS", 15, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
        ("Órion HPRS", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA", "LEVE"),
    ]

    cavalos_criados = []
    hoje = timezone.localdate()

    for nome, idade, ferradura, prop_nome, obs, dorme, local, treino in cavalos_dados:
        # Garante o proprietário
        dono, _ = Aluno.objects.get_or_create(nome=prop_nome, empresa=hprs, defaults={'telefone': "+5551991387872"})
        
        cav, _ = Cavalo.objects.update_or_create(
            nome=nome, empresa=hprs,
            defaults={
                'categoria': 'PROPRIO' if "HPRS" in nome else 'HOTELARIA',
                'proprietario': dono,
                'idade': idade,
                'usa_ferradura': 'SIM' if ferradura else 'NAO',
                'observacoes_medicas': obs,
                'onde_dorme': dorme,
                'piquete': piquete_principal if local == "PIQUETE" else None,
                'ultima_vacina': hoje - timedelta(days=random.randint(10, 200)),
                'ultimo_vermifugo': hoje - timedelta(days=random.randint(10, 80)),
            }
        )
        cavalos_criados.append(cav)

        # 6. DOCUMENTOS
        status_doc = 'VENCIDO' if "Danuza" in nome else 'EM_DIA'
        vencimento = hoje - timedelta(days=10) if status_doc == 'VENCIDO' else hoje + timedelta(days=60)
        DocumentoCavalo.objects.get_or_create(cavalo=cav, tipo='GTA', defaults={'status': status_doc, 'data_vencimento': vencimento})

    print(f"✅ {len(cavalos_criados)} Cavalos e Documentos processados.")

    # 7. ESTOQUE CRÍTICO
    estoque_itens = [
        ("Feno", 2, 10), ("Ração Algibeira", 3, 15), 
        ("Serragem", 1, 5), ("Alfafa", 2, 8)
    ]
    for nome_item, atual, min_alerta in estoque_itens:
        ItemEstoque.objects.get_or_create(
            nome=nome_item, empresa=hprs, 
            defaults={'quantidade_atual': atual, 'alerta_minimo': min_alerta, 'unidade_medida': 'FARDO'}
        )
    print("✅ Estoque crítico configurado.")

    # 8. HISTÓRICO DE TREINOS E AULAS (Nov/25 a Abr/26)
    print("⏳ Gerando histórico de 6 meses (Aulas e Treinos)...")
    data_ini = date(2025, 11, 1)
    data_fim = date(2026, 4, 30)
    delta = data_fim - data_ini

    for i in range(delta.days + 1):
        dia = data_ini + timedelta(days=i)
        if dia.weekday() == 6: continue  # Pula domingos

        # Gera 3 aulas por dia útil
        for _ in range(3):
            cav = random.choice(cavalos_criados)
            alu = random.choice(alunos_lista)
            prof = random.choice(professores)
            
            # Hora fictícia (09:00, 10:00 ou 15:00)
            hora = random.choice([9, 10, 15])
            dt_consciente = timezone.make_aware(timezone.datetime.combine(dia, timezone.datetime.min.time().replace(hour=hora)))

            Aula.objects.create(
                empresa=hprs, cavalo=cav, aluno=alu, professor=prof,
                data=dia, hora_inicio=dt_consciente, status='REALIZADA'
            )

    print("✨ SUCESSO TOTAL: Sistema HPRS totalmente preenchido e vinculado!")

if __name__ == "__main__":
    run()