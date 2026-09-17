@echo off
title Gate 4 - Local
color 0B
echo ==========================================
echo    INICIANDO GATE 4 - LOCAL
echo ==========================================
cd /d C:\_GestaoHipica\GATEAGORA
call venv\Scripts\activate
echo Servidor iniciando...
start http://127.0.0.1:8000/
python manage.py runserver
pause