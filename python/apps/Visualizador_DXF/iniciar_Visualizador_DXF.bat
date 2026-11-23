@echo off
setlocal EnableExtensions
rem ============================================================================
rem  Visualizador DXF - iniciador RAPIDO (app do SISTEMA - PPCPM)
rem
rem  Copia o CODIGO deste app (so o que mudou) pra uma pasta LOCAL deste PC e abre de la.
rem  Os DADOS continuam na pasta do servidor indicada em pasta_dados.txt (a mesma do unificador).
rem
rem  Uso:  iniciar_Visualizador_DXF.bat          abre sem janela preta (crie um atalho dele)
rem        iniciar_Visualizador_DXF.bat debug    abre com janela preta mostrando mensagens/erros
rem ============================================================================

set "ORIGEM=%~dp0"
if "%ORIGEM:~-1%"=="\" set "ORIGEM=%ORIGEM:~0,-1%"
set "LOCAL=%LOCALAPPDATA%\PPCP_Apps\Visualizador_DXF"
set "DEST=%LOCAL%\app"
set "DEBUG=0"
if /i "%~1"=="debug" set "DEBUG=1"

if not exist "%ORIGEM%\main.py" (
    echo [ERRO] main.py nao encontrado em "%ORIGEM%".
    pause
    exit /b 1
)

if not exist "%DEST%" mkdir "%DEST%"

if /i not "%ORIGEM%"=="%DEST%" (
    robocopy "%ORIGEM%" "%DEST%" /MIR /MT:8 /R:1 /W:1 /NFL /NDL /NJH /NJS /NP ^
        /XD "__pycache__" "referencia_html" "icones_usuario" "base_fixa" "envio_roteiro" "layouts_desktop" ^
        /XF *.db *.db-journal *.db-wal *.db-shm app_dxf_ppcp_log.txt* *.bak >nul
    if errorlevel 8 (
        if not exist "%DEST%\main.py" (
            echo [ERRO] Nao foi possivel copiar o programa para "%DEST%".
            pause
            exit /b 1
        )
        echo [AVISO] Falha ao atualizar a copia local; abrindo a versao ja copiada.
        if "%DEBUG%"=="1" pause
    )
)

rem o main.py le pasta_dados.txt a partir da pasta ORIGINAL (esta) e define PPCP_DADOS
set "PPCP_APP_ORIGEM=%ORIGEM%"

rem Python do SISTEMA - PPCPM (python\ferramentas\achar_python.bat): .venv do sistema, Python portatil ou o do PC
set "PYEXE="
set "PYARG="
if exist "%ORIGEM%\..\..\ferramentas\achar_python.bat" call "%ORIGEM%\..\..\ferramentas\achar_python.bat"
set "PYSIS=%PYEXE%"
if not defined PYEXE set "PYEXE=python"

if "%DEBUG%"=="1" (
    echo Codigo local : %DEST%
    echo Origem       : %ORIGEM%
    echo Log local    : %LOCAL%\logs\app_dxf_ppcp_log.txt
    echo Inicio       : %TIME%
    cd /d "%DEST%"
    "%PYEXE%" %PYARG% main.py
    echo Fim          : %TIME%
    pause
    exit /b 0
)

if not defined PYSIS goto python_do_pc
set "PYW=%PYSIS%"
if /i "%PYSIS:~-10%"=="python.exe" set "PYW=%PYSIS:~0,-10%pythonw.exe"
if /i "%PYSIS%"=="py" set "PYW=pyw"
if /i "%PYSIS%"=="python" set "PYW=pythonw"
start "" /D "%DEST%" "%PYW%" %PYARG% main.py
exit /b 0

:python_do_pc
where pythonw >nul 2>&1
if not errorlevel 1 (
    start "" /D "%DEST%" pythonw main.py
    exit /b 0
)
where pyw >nul 2>&1
if not errorlevel 1 (
    start "" /D "%DEST%" pyw -3 main.py
    exit /b 0
)
start "" /D "%DEST%" python main.py
exit /b 0
