@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM
cd /d "%~dp0"

echo ============================================
echo   SISTEMA - PPCPM  ^|  Grupo Projeart
echo ============================================
echo.

rem ---- procura o Python (nao precisa de administrador nem de pip) ----
set "PYEXE="
set "PYARG="

if exist ".python\python.exe" set "PYEXE=%~dp0.python\python.exe"
if defined PYEXE goto achou

py -3 -c "import sys" >nul 2>nul && (set "PYEXE=py" & set "PYARG=-3")
if defined PYEXE goto achou

python -c "import sys" >nul 2>nul && set "PYEXE=python"
if defined PYEXE goto achou

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if defined PYEXE goto achou
for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if defined PYEXE goto achou
for /d %%D in ("C:\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if defined PYEXE goto achou

rem ---- nao achou: baixa um Python portatil so para esta pasta ----
echo Python nao encontrado neste computador.
echo Baixando um Python portatil so para esta pasta (sem instalar, sem administrador)...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';[Net.ServicePointManager]::SecurityProtocol='Tls12';" ^
  "$z=Join-Path $env:TEMP 'ppcpm-python.zip';" ^
  "Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $z -UseBasicParsing;" ^
  "Expand-Archive $z -DestinationPath '.python' -Force; Remove-Item $z"
if exist ".python\python.exe" (
  set "PYEXE=%~dp0.python\python.exe"
  goto achou
)
echo.
echo [ERRO] Nao foi possivel baixar o Python (a rede da empresa pode bloquear).
echo Instale o Python por um destes caminhos e abra este arquivo de novo:
echo   1. Microsoft Store: procure "Python 3.12" e clique em Obter (nao pede administrador)
echo   2. Site https://www.python.org/downloads/  -  marque "Add python.exe to PATH"
echo.
pause
exit /b 1

:achou
echo Python encontrado. Abrindo o sistema no navegador...
echo.
"%PYEXE%" %PYARG% app.py %*
echo.
pause
