@echo off
setlocal enabledelayedexpansion

set "SSH_KEY=C:\_oracle\ssh-key-2026-03-23.key"
set "SSH_USER=ubuntu"
set "SSH_HOST=137.131.251.83"
set "BACKUP_DIR=C:\_gate4_backups"
set "APP_PATH=/home/ubuntu/gateagora"

echo [%date% %time%] === RESTAURACAO GATE4 ===
echo.
echo Arquivos disponiveis:
echo.

setlocal enabledelayedexpansion
set "contador=0"
for /f "delims=" %%f in ('dir "%BACKUP_DIR%\*.json" /b /o:-d') do (
    set /a contador+=1
    echo   !contador!. %%f
    set "arquivo_!contador!=%%f"
)

if %contador% equ 0 (
    echo [ERRO] Nenhum backup encontrado em %BACKUP_DIR%
    pause
    exit /b 1
)

echo.
set /p escolha="Digite o numero do arquivo a restaurar (1-%contador%): "

if not defined arquivo_!escolha! (
    echo [ERRO] Opcao invalida
    pause
    exit /b 1
)

set "ARQUIVO=!arquivo_%escolha%!"
set "ARQUIVO_COMPLETO=%BACKUP_DIR%\!ARQUIVO!"

echo.
echo Arquivo selecionado: !ARQUIVO!
echo.

echo [1/2] Copiando arquivo para o servidor...
scp -i "%SSH_KEY%" "!ARQUIVO_COMPLETO!" %SSH_USER%@%SSH_HOST%:/tmp/!ARQUIVO!

if %errorlevel% neq 0 (
    echo [ERRO] Copia falhou!
    pause
    exit /b 1
)

echo [OK] Arquivo copiado
echo.

echo [2/2] Restaurando dados...
ssh -i "%SSH_KEY%" %SSH_USER%@%SSH_HOST% "cd %APP_PATH% && source venv/bin/activate && python manage.py loaddata /tmp/!ARQUIVO!"

if %errorlevel% neq 0 (
    echo [ERRO] Restauracao falhou!
    pause
    exit /b 1
)

echo.
echo [SUCESSO] Backup restaurado!
echo Dados voltaram ao estado de: !ARQUIVO!
echo.

pause
endlocal