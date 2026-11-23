@echo off
setlocal EnableExtensions
rem Instala as bibliotecas do app Corte Inteligente no Python do SISTEMA - PPCPM (sem PowerShell)
set "ORIGEM=%~dp0"
set "PYEXE="
set "PYARG="
if exist "%ORIGEM%..\..\ferramentas\achar_python.bat" call "%ORIGEM%..\..\ferramentas\achar_python.bat"
if not defined PYEXE set "PYEXE=python"
echo Instalando as bibliotecas de Corte Inteligente ...
"%PYEXE%" %PYARG% -m pip install -r "%ORIGEM%requirements.txt"
if errorlevel 1 goto erro
echo.
echo Pronto. Agora abra pelo iniciar_*.bat desta pasta.
pause
exit /b 0
:erro
echo.
echo [ERRO] Nao foi possivel instalar. Sem internet? Use o BAIXAR_PACOTES_OFFLINE.bat do sistema num PC liberado.
pause
exit /b 1
