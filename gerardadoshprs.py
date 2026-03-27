# -*- coding: utf-8 -*-
import os
import django
import random
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gateagora.settings')
django.setup()

from django.contrib.auth.models import User
from gateagora.models import (
    Empresa, Perfil, Aluno, Baia, Piquete, Cavalo, 
    Aula, ItemEstoque, DocumentoCavalo, RegistroOcorrencia, ConfigPrazoManejo
)

def run():
    print("🚀 Iniciando cadastro seguro para Hípica Paraíso RS...")

    # 1. EMPRESA
    hprs, _ = Empresa.objects.get_or_create(
        slug="hipica-paraiso-rs",
        defaults={'nome': "Hípica Paraíso RS", 'cidade': "Portão/RS"}
    )

    # 2. USUÁRIOS (Senha Padrão: Dado$Verde)
    def criar_usuario(username, senha, cargo):
        u, created = User.objects.get_or_create(username=username)
        if created:
            u.set_password(senha)
            u.save()
        Perfil.objects.get_or_create(user=u, empresa=hprs, defaults={'cargo': cargo})
        return u

    # Gestoras e Professores
    criar_usuario("Suzana", "Asterix", 'Gestor') # Senha mestre da proprietária
    criar_usuario("Dado", "Dado$Verde", 'Professor') 
    criar_usuario("Suzana Schuch", "Dado$Verde", 'Professor')
    criar_usuario("Alessandro", "Dado$Verde", 'Professor')
    criar_usuario("Luiza Squeff", "Dado$Verde", 'Professor')

    # Tratadores
    criar_usuario("Rodrigo", "Dado$Verde", 'Tratador')
    criar_usuario("Maurício", "Dado$Verde", 'Tratador')

    # 3. ESTRUTURA E CAVALOS
    aluno_haras, _ = Aluno.objects.get_or_create(nome="Haras Paraíso RS", empresa=hprs, defaults={'telefone': "+5551991387872"})
    piquete_principal, _ = Piquete.objects.get_or_create(nome="Piquete Principal", empresa=hprs, defaults={'capacidade': 20})

    cavalos_dados = [
        ("Galileu HPRS", 6, False, "Haras Paraíso RS", "Dores na pata", "PIQUETE", "PIQUETE"),
        ("Baruk", 8, True, "Cecília", "Muito magro", "BAIA", "PIQUETE"),
        ("Jade", 12, True, "Camila", "Sem dores", "BAIA", "PIQUETE"),
        ("Soneto", 8, True, "Luciana", "Recuperando cirurgia", "BAIA", "PIQUETE"),
        ("Zenda", 8, True, "Camila", "Dores na paleta", "BAIA", "PIQUETE"),
        ("Catita", 19, True, "Maria Hemília", "Sem obs", "BAIA", "PIQUETE"),
        ("Handover", 9, True, "Camila", "Manca e aerofágico", "BAIA", "PIQUETE"),
        ("Charlote", 9, False, "Júlia", "Sem obs", "BAIA", "PIQUETE"),
        ("Pegaus", 6, True, "Marcelo", "Sem obs", "BAIA", "PIQUETE"),
        ("Pé de Pano HPRS", 29, False, "Haras Paraíso RS", "Baixa visão", "BAIA", "PIQUETE"),
        ("Bailarina", 8, True, "Júlia", "Sem obs", "BAIA", "BAIA"),
        ("Havaiano", 12, True, "Cecília", "Muito magro", "BAIA", "PIQUETE"),
        ("Gringa", 8, False, "Marcela", "Sem obs", "BAIA", "PIQUETE"),
        ("Gatiada HPRS", 36, False, "Haras Paraíso RS", "Pouca visão", "BAIA", "BAIA"),
        ("Fina Flor HPRS", 23, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Braína HPRS", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Danuza HPRS", 12, False, "Haras Paraíso RS", "Documentos vencidos", "BAIA", "BAIA"),
        ("Amiga HPRS", 12, False, "Haras Paraíso RS", "Obs respiração", "BAIA", "BAIA"),
        ("Bordada HPRS", 12, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Aromah HPRS", 11, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Fênix HPRS", 10, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Badalada HPRS", 16, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Jobin HPRS", 5, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Zeus", 7, False, "Luísa", "Sem obs", "BAIA", "BAIA"),
        ("Asterix HPRS", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Duque HPRS", 15, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
        ("Órion HPRS", 17, False, "Haras Paraíso RS", "Sem obs", "BAIA", "BAIA"),
    ]

    for nome, idade, ferradura, prop_nome, obs, dorme, local in cavalos_dados:
        dono, _ = Aluno.objects.get_or_create(nome=prop_nome, empresa=hprs, defaults={'telefone': "+5551991387872"})
        cav, created = Cavalo.objects.get_or_create(
            nome=nome, empresa=hprs,
            defaults={
                'categoria': 'PROPRIO' if "HPRS" in nome else 'HOTELARIA',
                'proprietario': dono, 'onde_dorme': dorme,
                'piquete': piquete_principal if local == "PIQUETE" else None,
                'ultima_vacina': timezone.localdate() - timedelta(days=60)
            }
        )
        if created: print(f"✅ Cavalo {nome} cadastrado.")

    print("✨ Processo finalizado!")

if __name__ == "__main__":
    run()