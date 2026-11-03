@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM - Baixar pacotes para PCs sem internet
cd /d "%~dp0"
echo Baixa todas as bibliotecas para a pasta "pacotes".
echo Depois copie a pasta inteira do sistema (com "pacotes") para o outro PC
echo e rode INSTALAR_BIBLIOTECAS.bat la - instala sem internet.
echo Use a MESMA versao do Python nos dois PCs.
echo.
call "%~dp0ferramentas\achar_python.bat"
if not defined PYEXE (
  echo [ERRO] Python nao encontrado.
  pause
  exit /b 1
)
"%PYEXE%" %PYARG% -m pip download --disable-pip-version-check -r bibliotecas\todas.txt -d pacotes
if errorlevel 1 (
  echo [ERRO] Falha ao baixar. Confira a internet.
  pause
  exit /b 1
)
echo.
echo Pronto: pasta "pacotes" criada.
pause
