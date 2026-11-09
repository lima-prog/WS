@echo off
rem Procura o Python deste PC. Uso: call ferramentas\achar_python.bat [real]
rem   real = ignora o .venv e o Python portatil (precisa de um Python instalado, para criar o .venv)
set "PYEXE="
set "PYARG="
set "RAIZ=%~dp0.."
if /i "%~1"=="real" goto procurar
rem O .venv so vale se funciona NESTE PC (um .venv copiado de outro computador aponta para o Python de la)
if exist "%RAIZ%\.venv\Scripts\python.exe" "%RAIZ%\.venv\Scripts\python.exe" -c "import sys" >nul 2>nul && (set "PYEXE=%RAIZ%\.venv\Scripts\python.exe" & goto :eof)
if exist "%RAIZ%\.python\python.exe" "%RAIZ%\.python\python.exe" -c "import sys" >nul 2>nul && (set "PYEXE=%RAIZ%\.python\python.exe" & goto :eof)
:procurar
py -3 -c "import sys" >nul 2>nul && (set "PYEXE=py" & set "PYARG=-3" & goto :eof)
python -c "import sys" >nul 2>nul && (set "PYEXE=python" & goto :eof)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if defined PYEXE goto :eof
for /d %%D in ("%ProgramFiles%\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
if defined PYEXE goto :eof
for /d %%D in ("C:\Python3*") do if exist "%%D\python.exe" set "PYEXE=%%D\python.exe"
goto :eof
