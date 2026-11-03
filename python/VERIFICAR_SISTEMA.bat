@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM - Verificar
cd /d "%~dp0"
call "%~dp0ferramentas\achar_python.bat"
if not defined PYEXE (
  echo [FALTA] Python nao encontrado. Abra o ABRIR_SISTEMA.bat primeiro.
  pause
  exit /b 1
)
"%PYEXE%" %PYARG% app.py --verificar
echo.
pause
