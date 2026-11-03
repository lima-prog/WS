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
if not defined PYEXE call :portatil
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

:portatil
echo Python nao encontrado neste computador.
echo Baixando um Python portatil so para esta pasta - sem instalar, sem administrador...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';[Net.ServicePointManager]::SecurityProtocol='Tls12';" ^
  "$z=Join-Path $env:TEMP 'ppcpm-python.zip';" ^
  "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $z -UseBasicParsing;" ^
  "Expand-Archive $z -DestinationPath '.python' -Force; Remove-Item $z"
if exist "%~dp0.python\python.exe" set "PYEXE=%~dp0.python\python.exe"
goto :eof

:sem_python
echo.
echo [ERRO] Nao foi possivel baixar o Python - a rede da empresa pode bloquear.
echo Instale o Python por um destes caminhos e abra este arquivo de novo:
echo   1. Microsoft Store: procure "Python 3.12" e clique em Obter - nao pede administrador
echo   2. Site https://www.python.org/downloads/  -  marque "Add python.exe to PATH"
echo.
pause
exit /b 1
