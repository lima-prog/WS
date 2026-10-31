@echo off
chcp 65001 >nul
title SISTEMA - PPCPM
cd /d "%~dp0"

echo ============================================
echo   SISTEMA - PPCPM  ^|  Grupo Projeart
echo ============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo [ERRO] Python nao encontrado neste computador.
  echo Instale o Python 3.10 ou mais novo em https://www.python.org/downloads/
  echo e marque a opcao "Add python.exe to PATH" na instalacao.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Preparando o sistema pela primeira vez, aguarde...
  %PY% -m venv .venv || (echo [ERRO] Nao foi possivel criar o ambiente. & pause & exit /b 1)
)

echo Conferindo os componentes...
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || (echo [ERRO] Falha ao instalar os componentes. Confira a internet. & pause & exit /b 1)

echo.
echo Abrindo o sistema no navegador...
echo Para fechar o sistema, feche esta janela ou aperte Ctrl+C.
echo.
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:5000"
".venv\Scripts\python.exe" app.py %*
pause
