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
robocopy "%~dp0." "%DEST%" /E /NFL /NDL /NJH /NJS /NP /XD .venv __pycache__ >nul
if errorlevel 8 (
  echo [ERRO] Nao foi possivel copiar para %DEST%.
  pause
  exit /b 1
)

:pronto
echo.
echo Pronto! O sistema esta em: %DEST%
echo.
echo Falta so o atalho na Area de Trabalho - 3 cliques:
echo   1. Na pasta que vai abrir agora, clique com o botao direito em ABRIR_SISTEMA
echo   2. Mostrar mais opcoes  -^>  Enviar para  -^>  Area de trabalho (criar atalho)
echo   3. Na Area de Trabalho, renomeie o atalho para: SISTEMA - PPCPM
echo.
start "" explorer "%DEST%"
pause
