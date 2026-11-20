@echo off
title Robot de Jurisprudencia Judicial - Colombia ^& Google Drive
echo ====================================================================
echo   INICIANDO ROBOT DE JURISPRUDENCIA JUDICIAL Y DESCARGA A DRIVE
echo ====================================================================
echo.
echo Verificando dependencias...
python -m pip install -r requirements.txt --quiet
echo.
echo Iniciando servidor web en http://localhost:8000
echo Abriendo navegador...
start http://localhost:8000
echo.
python main.py
pause
