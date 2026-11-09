@echo off
setlocal EnableExtensions
chcp 65001 >nul
title SISTEMA - PPCPM - Instalar neste PC
rem pushd funciona tambem no drive da rede (X:\ ou \\servidor\pasta)
pushd "%~dp0"

echo ============================================
echo   Instalar o SISTEMA - PPCPM neste PC
echo ============================================
echo.
set "ORIGEM=%CD%"
set "DEST=%USERPROFILE%\SISTEMA-PPCPM"

rem O sistema roda SEMPRE de uma pasta do proprio PC (nunca do drive da rede):
rem cada PC tem o seu Python, as suas bibliotecas e os seus dados.
if /i "%ORIGEM%"=="%DEST%" goto copiado
echo Copiando o sistema para %DEST% ...
echo (a pasta .venv e os dados de quem colocou no drive NAO sao copiados)
robocopy "%ORIGEM%" "%DEST%" /E /NFL /NDL /NJH /NJS /NP /R:2 /W:2 /XD .venv __pycache__ dados_locais .atualizando /XF *.log >nul
if errorlevel 8 (
  echo [ERRO] Nao foi possivel copiar para %DEST%.
  popd
  pause
  exit /b 1
)

:copiado
popd
cd /d "%DEST%"
echo Pronto! O sistema esta em: %DEST%
echo.
rem .venv que nao funciona neste PC (veio de outro computador): tira, o INSTALAR_BIBLIOTECAS cria um novo
if exist ".venv\Scripts\python.exe" ".venv\Scripts\python.exe" -c "import sys" >nul 2>nul || rmdir /s /q ".venv" >nul 2>nul

call "%DEST%\ferramentas\achar_python.bat" real
if not defined PYEXE goto sem_python
"%PYEXE%" %PYARG% app.py --criar-atalho
echo O atalho SISTEMA - PPCPM fica na Area de Trabalho.
echo.
echo Agora instalando as bibliotecas (precisa de internet, leva alguns minutos)...
echo.
call "%DEST%\INSTALAR_BIBLIOTECAS.bat"
exit /b 0

:sem_python
echo [FALTA] Python nao encontrado neste PC.
echo   1. Abra a Microsoft Store, procure "Python 3.12" e clique em Obter - nao pede administrador.
echo   2. Depois rode este INSTALAR de novo, pelo drive.
echo.
pause
exit /b 1
