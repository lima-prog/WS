@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM - Instalar bibliotecas
cd /d "%~dp0"

rem Uso: INSTALAR_BIBLIOTECAS.bat            -> todas as secoes
rem      INSTALAR_BIBLIOTECAS.bat pg12       -> so a secao Impressao de Etiquetas (veja bibliotecas\BIBLIOTECAS.md)
set "LISTA=bibliotecas\todas.txt"
if not "%~1"=="" set "LISTA=bibliotecas\%~1.txt"
if not exist "%LISTA%" (
  echo [ERRO] Lista nao encontrada: %LISTA%
  pause
  exit /b 1
)

echo ============================================
echo   Instalando bibliotecas: %LISTA%
echo ============================================
echo.

if exist ".venv\Scripts\python.exe" goto instalar
call "%~dp0ferramentas\achar_python.bat" real
if not defined PYEXE (
  echo [ERRO] Para instalar bibliotecas e preciso o Python instalado no PC - o portatil nao serve.
  echo Instale pela Microsoft Store: "Python 3.12" - nao pede administrador. Depois abra este arquivo de novo.
  pause
  exit /b 1
)
echo Criando a pasta .venv - ambiente proprio do sistema, nao mexe no resto do PC...
"%PYEXE%" %PYARG% -m venv .venv
if errorlevel 1 (
  echo [ERRO] Nao foi possivel criar o .venv.
  pause
  exit /b 1
)

:instalar
set "VPY=.venv\Scripts\python.exe"
if exist "pacotes\" (
  echo Instalando SEM internet, pela pasta "pacotes"...
  "%VPY%" -m pip install --no-index --find-links pacotes -r "%LISTA%"
) else (
  echo Instalando pela internet...
  "%VPY%" -m pip install --disable-pip-version-check -r "%LISTA%"
)
if errorlevel 1 (
  echo.
  echo [ERRO] A instalacao falhou. Se a rede da empresa bloqueia, use o modo sem internet:
  echo   1. Num PC com internet, rode BAIXAR_PACOTES_OFFLINE.bat
  echo   2. Copie a pasta "pacotes" para esta pasta e rode este arquivo de novo.
  pause
  exit /b 1
)
echo.
"%VPY%" app.py --verificar
echo.
echo Pronto. O ABRIR_SISTEMA.bat passa a usar este ambiente sozinho.
pause
