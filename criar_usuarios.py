# -*- coding: utf-8 -*-
import os
import django
import getpass
import sys
from pathlib import Path

print("⏳ Iniciando diagnóstco de caminhos...")

# === SISTEMA DE AUTO-LOCALIZAÇÃO DE CONFIGURAÇÕES ===
# Este bloco busca o settings.py automaticamente para corrigir o erro
# "ModuleNotFoundError: No module named '...settings'"

# 1. Define a pasta raiz do projeto (C:\_GestaoHipica\GATEAGORA)
# O script assume que está na raiz.
BASE_DIR = Path(__file__).resolve().parent

# 2. Adiciona a raiz ao sys.path para o Python encontrar os pacotes
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))
    print(f"✅ Raiz do projeto adicionada ao PATH: {BASE_DIR}")

# 3. Busca automática pelo arquivo settings.py
print("🔍 Buscando arquivo settings.py dentro do projeto...")
config_files = list(BASE_DIR.glob('**/settings.py'))

# Filtra para evitar pegar settings.py dentro da venv (se houver cópia)
config_files = [f for f in config_files if 'venv' not in str(f)]

if not config_files:
    print("\n❌ ERRO CRÍTICO: Não consegui encontrar o arquivo 'settings.py'!")
    print(f"Procurei dentro de: {BASE_DIR}")
    print("Verifique se o arquivo existe e se você está rodando o script na pasta correta.")
    print("\n----------------------------------------------")
    raise FileNotFoundError("Arquivo settings.py não encontrado.")

# Pega o primeiro settings.py encontrado (geralmente é o correto)
settings_path = config_files[0]
print(f"✅ Arquivo settings.py encontrado em: {settings_path}")

# 4. Descobre o nome da pasta que contém o settings.py (o pacote de configuração)
# Ex: Se achou em ...\GATEAGORA\gateagora\settings.py, o pacote é 'gateagora'
# Ex: Se achou em ...\GATEAGORA\config\settings.py, o pacote é 'config'
nome_pacote_config = settings_path.parent.name
print(f"📦 Pacote de configuração detectado: '{nome_pacote_config}'")

# 5. Define a variável de ambiente para o Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{nome_pacote_config}.settings')
# ====================================================

try:
    print("⏳ Inicializando ambiente Django...")
    django.setup()
    print("✅ Ambiente Django inicializado com sucesso!")
    
    # Importações dos models após o setup do Django
    from django.contrib.auth.models import User
    from gateagora.models import Empresa, Perfil
except Exception as e:
    print("\n❌ ERRO CRÍTICO NA INICIALIZAÇÃO DO DJANGO ❌")
    print("----------------------------------------------")
    print("Erro detalhado:")
    print(e)
    
    # Verificação adicional se os models não foram encontrados
    if "ModuleNotFoundError" in str(e) and "gateagora.models" in str(e):
        print("\n💡 DICA: O Django foi configurado, mas não encontrei o app 'gateagora'.")
        print("Verifique se a pasta 'gateagora' (que contém models.py) existe na raiz.")
    
    print("----------------------------------------------")
    raise e


def main_process():
    print("\n🚀 --- Gerador Interativo de Usuários Multi-Empresa ---")
    print("-------------------------------------------------------")

    # 1. Seleção da Empresa de forma dinâmica
    empresa = None
    while not empresa:
        try:
            empresas_ativas = Empresa.objects.all()
            if not empresas_ativas.exists():
                print("\n⚠️ Nenhuma empresa cadastrada no banco de dados.")
                print("Cadastre uma empresa pelo painel administrativo antes de continuar.")
                return 
                
            print("\nEmpresas cadastradas no sistema:")
            for emp in empresas_ativas:
                print(f"  - [{emp.slug}] {emp.nome} ({emp.cidade})")
        except Exception as e:
            print(f"❌ Erro ao consultar empresas no banco de dados: {e}")
            return

        slug_input = input("\nDigite o SLUG da empresa onde o usuário será criado (ou 'sair' para cancelar): ").strip()
        
        if slug_input.lower() == 'sair':
            return

        if not slug_input:
            print("❌ O slug não pode ser vazio.")
            continue

        try:
            empresa = Empresa.objects.get(slug=slug_input)
            print(f"🏢 Empresa selecionada: {empresa.nome}")
        except Empresa.DoesNotExist:
            print(f"❌ Erro: Empresa com slug '{slug_input}' não encontrada. Tente novamente.")

    # 2. Coleta de dados do novo usuário de forma dinâmica
    print("\n--- Dados do Novo Usuário ---")
    
    username = ""
    while not username:
        username = input("Nome de usuário (Login): ").strip()
        if not username: print("❌ O username não pode ser vazio.")
        if User.objects.filter(username=username).exists():
            print(f"⚠️ Aviso: O usuário '{username}' já existe. A senha será ATUALIZADA e ele será vinculado à empresa {empresa.nome}.")

    # Coleta segura da senha
    senha = ""
    while not senha:
        senha = getpass.getpass("Senha (não aparecerá ao digitar): ")
        if not senha: 
            print("❌ A senha não pode ser vazia.")
            continue
        
        # Confirmação de senha
        confirmacao = getpass.getpass("Confirme a senha: ")
        if senha != confirmacao:
            print("❌ As senhas não coincidem. Tente novamente.")
            senha = "" # Reseta para forçar o loop

    # Coleta e validação do cargo
    cargo = ""
    # Defina aqui os cargos exatamente como estão no seu modelo/banco
    # Se der erro aqui, verifique as escolhas no seu model Perfil
    CARGOS_VALIDOS = ['Gestor', 'Professor', 'Recepcionista', 'Veterinário']
    while cargo not in CARGOS_VALIDOS:
        print(f"Cargos permitidos: {', '.join(CARGOS_VALIDOS)}")
        cargo = input("Cargo do usuário: ").strip().capitalize()
        if cargo not in CARGOS_VALIDOS:
            print(f"❌ Cargo inválido. Digite exatamente um dos permitidos.")

    # 3. Processo de criação/atualização
    print(f"\n⏳ Criando/Atualizando usuário '{username}' na empresa '{empresa.nome}'...")

    try:
        # Busca o usuário ou cria se não existir
        u, created = User.objects.get_or_create(username=username)
        u.set_password(senha)
        u.is_staff = True  # Permite entrar no painel administrativo
        u.is_active = True
        u.save()
        
        # Vincula ou atualiza o perfil da empresa
        perfil, p_created = Perfil.objects.get_or_create(
            user=u, 
            empresa=empresa, 
            defaults={'cargo': cargo}
        )

        # Se o perfil já existia mas o cargo era diferente, atualizamos
        if not p_created and perfil.cargo != cargo:
            perfil.cargo = cargo
            perfil.save()
            print(f"✅ Cargo do usuário atualizado para '{cargo}'.")

        status = "criado" if created else "atualizado"
        print(f"✅ Usuário '{username}' {status} com sucesso e vinculado à '{empresa.nome}'.")
    except Exception as e:
        print(f"❌ Erro durante a criação do usuário no banco de dados: {e}")


if __name__ == "__main__":
    try:
        main_process()
    except KeyboardInterrupt:
        print("\n\n👋 Execução cancelada pelo usuário.")
    except Exception as e:
        import traceback
        print("\n❌ OCORREU UM ERRO INESPERADO ❌")
        print("---------------------------------")
        traceback.print_exc()
        print("---------------------------------")
        sys.exit(1) # Informa ao .bat que deu erro