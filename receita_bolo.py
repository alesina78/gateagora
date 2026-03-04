import os
import subprocess
import sys

def preparar_gateagora():
    print("--- 🐎 GATEAGORA: MONTANDO O SISTEMA ---")
    
    # 1. Instala o que falta (Django e o Visual Bonito)
    print("Instalando as ferramentas de luxo...")
    subprocess.run([sys.executable, "-m", "pip", "install", "django", "django-unfold"])

    # 2. Cria o projeto se não existir
    if not os.path.exists("manage.py"):
        print("Criando base do projeto...")
        subprocess.run(["django-admin", "startproject", "core", "."])
        subprocess.run([sys.executable, "manage.py", "startapp", "gateagora"])

    # 3. Configura o visual Esmeralda da GateAgOra
    settings_path = "core/settings.py"
    with open(settings_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Adiciona o Unfold e a App na lista de instalados
    if "'unfold'," not in content:
        content = content.replace("INSTALLED_APPS = [", "INSTALLED_APPS = [\n    'unfold',\n    'gateagora',")
        content += "\n\nUNFOLD = {'SITE_TITLE': 'GateAgOra', 'COLORS': {'primary': {'500': '16, 185, 129'}}}"
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(content)

    # 4. Cria o Banco de Dados
    print("Preparando as tabelas de cavalos e alunos...")
    subprocess.run([sys.executable, "manage.py", "migrate"])

    print("\n--- ✅ TUDO PRONTO! ---")
    print("Para ver o sistema:")
    print("1. No terminal abaixo, digite: python manage.py runserver")
    print("2. Abra o navegador em: http://127.0.0.1:8000/admin")

if __name__ == "__main__":
    preparar_gateagora()