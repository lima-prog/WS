@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM - Instalar neste PC
cd /d "%~dp0"

echo ============================================
echo   Instalar o SISTEMA - PPCPM neste PC
echo ============================================
echo.
set "DEST=%~dp0"
if "%DEST:~-1%"=="\" set "DEST=%DEST:~0,-1%"

rem Se esta rodando de Downloads ou de dentro do .zip, copia para uma pasta fixa
echo %DEST% | findstr /i /c:"\Downloads\" /c:"\AppData\Local\Temp\" >nul
if errorlevel 1 goto pronto
set "DEST=%USERPROFILE%\SISTEMA-PPCPM"
echo Copiando o sistema para %DEST% ...
robocopy "%~dp0." "%DEST%" /E /NFL /NDL /NJH /NJS /NP /XD .venv __pycache__ dados_locais >nul
if errorlevel 8 (
  echo [ERRO] Nao foi possivel copiar para %DEST%.
  pause
  exit /b 1
)

:pronto
echo.
echo Pronto! O sistema esta em: %DEST%
echo.
rem .venv copiado de outro PC (aponta para o Python de la): tira, o INSTALAR_BIBLIOTECAS cria um novo
if exist "%DEST%\.venv\Scripts\python.exe" "%DEST%\.venv\Scripts\python.exe" -c "import sys" >nul 2>nul || rmdir /s /q "%DEST%\.venv" >nul 2>nul
call "%DEST%\ferramentas\achar_python.bat"
if not defined PYEXE goto atalho_manual
"%PYEXE%" %PYARG% "%DEST%\app.py" --criar-atalho
echo.
echo O atalho SISTEMA - PPCPM esta na Area de Trabalho.
echo Agora rode INSTALAR_BIBLIOTECAS (na pasta que vai abrir) para os programas em Python.
echo.
start "" explorer "%DEST%"
pause
exit /b 0

:atalho_manual
echo Python nao encontrado. Instale o "Python 3.12" pela Microsoft Store e rode este arquivo de novo.
echo.
start "" explorer "%DEST%"
pause
