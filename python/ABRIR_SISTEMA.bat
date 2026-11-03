@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM
cd /d "%~dp0"

echo ============================================
echo   SISTEMA - PPCPM  ^|  Grupo Projeart
echo ============================================
echo.

call "%~dp0ferramentas\achar_python.bat"
if not defined PYEXE goto sem_python

set "ARGS=%*"
:rodar
"%PYEXE%" %PYARG% app.py %ARGS%
set "COD=%errorlevel%"
if "%COD%"=="3" goto reabrir
if "%COD%"=="0" exit /b 0
echo.
echo O sistema fechou com erro - codigo %COD%. Mande um print desta janela.
pause
exit /b %COD%

:reabrir
echo.
echo Versao nova instalada. Reabrindo o sistema...
timeout /t 2 /nobreak >nul
set "ARGS=%* --sem-navegador"
goto rodar

:sem_python
echo [ERRO] Python nao encontrado neste computador.
echo Instale o Python por um destes caminhos e abra este arquivo de novo:
echo   1. Microsoft Store: procure "Python 3.12" e clique em Obter - nao pede administrador
echo   2. Site https://www.python.org/downloads/  -  marque "Add python.exe to PATH"
echo.
pause
exit /b 1
