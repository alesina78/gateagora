@echo off
title Criador de Usuarios Gate4 - Interativo
cls

echo =======================================================
echo     INICIALIZANDO CRIADOR DE USUARIOS INTERATIVO
echo =======================================================
echo.

:: 1. Define as variáveis de caminho (Ajuste se necessário)
set PROJETO_DIR=C:\_GestaoHipica\GATEAGORA
set SCRIPT_NAME=criar_usuarios.py

:: 2. Entra no diretório do projeto
echo [1/4] Acessando diretorio do projeto...
if not exist "%PROJETO_DIR%\manage.py" (
    echo.
    echo ❌ ERRO: Arquivo manage.py nao encontrado em %PROJETO_DIR%
    echo Verifique se o caminho na variavel PROJETO_DIR no início deste arquivo .bat esta correto.
    goto final
)
cd /d "%PROJETO_DIR%"

:: 3. Ativa o Ambiente Virtual
echo [2/4] Ativando ambiente virtual...
if not exist "venv\Scripts\activate.bat" (
    echo.
    echo ❌ ERRO: Ambiente virtual nao encontrado em %PROJETO_DIR%\venv
    echo Certifique-se de que a venv existe e o nome da pasta e 'venv'.
    goto final
)
call venv\Scripts\activate.bat

:: 4. Configura o PYTHONPATH (Isso resolve o erro "No module named gateagora")
echo [3/4] Configurando caminhos do Python...
set PYTHONPATH=%PROJETO_DIR%;%PYTHONPATH%

:: 5. Executa o script Python
echo [4/4] Iniciando script Python...
echo -------------------------------------------------------
if not exist "%SCRIPT_NAME%" (
    echo.
    echo ❌ ERRO: O script Python '%SCRIPT_NAME%' nao foi encontrado na pasta.
    echo Certifique-se de salvar o arquivo .py com este nome na mesma pasta deste .bat.
    deactivate
    goto final
)
python "%SCRIPT_NAME%"

:final
echo.
echo =======================================================
echo     PROCESSO FINALIZADO
echo =======================================================
pause