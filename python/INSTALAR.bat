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
if errorlevel 1 goto atalhos
set "DEST=%USERPROFILE%\SISTEMA-PPCPM"
echo Copiando o sistema para %DEST% ...
robocopy "%~dp0." "%DEST%" /E /NFL /NDL /NJH /NJS /NP /XD .venv __pycache__ >nul
if errorlevel 8 (
  echo [ERRO] Nao foi possivel copiar para %DEST%.
  pause
  exit /b 1
)

:atalhos
powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\ferramentas\atalhos.ps1" -Pasta "%DEST%"
echo.
choice /c SN /n /m "Abrir o sistema sozinho quando o Windows ligar? [S/N] "
if errorlevel 2 (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\ferramentas\atalhos.ps1" -Pasta "%DEST%" -TirarInicio
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%DEST%\ferramentas\atalhos.ps1" -Pasta "%DEST%" -Inicio
)
echo.
echo Pronto! Use o atalho "SISTEMA - PPCPM" na Area de Trabalho.
echo Pasta do sistema: %DEST%
echo.
pause
