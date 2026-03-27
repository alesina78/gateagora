@echo off
title Gate 4 Cloud - Inicializador
color 0B

echo ==========================================
echo    INICIALIZANDO GATE 4 MANAGEMENT
echo ==========================================

echo [1/4] Ligando a Maquina no Fly.io...
call fly machine start 286501db745d58

echo.
echo [2/4] Aguardando 5 segundos para o sistema subir...
timeout /t 5 /nobreak > nul

echo.
echo [3/4] Populando Banco de Dados (Cavalos e Financeiro)...
call fly ssh console -C "python manage.py popular_db"

echo.
echo [4/4] Vinculando seu usuario como Gestor...
call fly ssh console -C "python manage.py shell -c \"from django.contrib.auth.models import User; from gateagora.models import Empresa, Perfil; e=Empresa.objects.first(); u=User.objects.get(username='alessandro_admin'); Perfil.objects.update_or_create(user=u, defaults={'empresa': e, 'cargo': 'Gestor'}); print('### VINCULO OK ###')\""

echo.
echo ==========================================
echo    PROCESSO CONCLUIDO COM SUCESSO!
echo ==========================================
echo Abrindo o site agora...
start https://gate4-app.fly.dev/

pause