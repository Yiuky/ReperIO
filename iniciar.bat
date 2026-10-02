@echo off
:: ============================================================================
:: ReperIO - lancador para Windows
::
:: 1) Procura um Python 3.8+ COM tkinter ja instalado na maquina e roda o
::    reperio.py com ele (modo isolado: -I ignora PYTHONHOME/PYTHONPATH,
::    que o ArcGIS 10.x costuma deixar apontando para o Python 2.7).
:: 2) Se nao houver, abre o ReperIO.exe (nao precisa de Python).
::
:: Para forcar um interpretador:  set REPERIO_PYTHON=C:\caminho\python.exe
:: ============================================================================
setlocal
set "APP=%~dp0reperio.py"
set "EXE=%~dp0ReperIO.exe"
set "PYEXE="

if not exist "%APP%" goto :use_exe

if defined REPERIO_PYTHON call :try "%REPERIO_PYTHON%"
if not defined PYEXE if defined GFF_PYTHON call :try "%GFF_PYTHON%"
if not defined PYEXE for /f "delims=" %%P in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do call :try "%%P"
if not defined PYEXE call :try "%ProgramFiles%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
if not defined PYEXE for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "%ProgramFiles%\Python3*") do call :try "%%~D\python.exe"
if not defined PYEXE for /f "delims=" %%P in ('where python 2^>nul') do call :try "%%P"
if not defined PYEXE goto :use_exe

set "PYW=%PYEXE:python.exe=pythonw.exe%"
if not exist "%PYW%" set "PYW=%PYEXE%"
start "" "%PYW%" -I "%APP%" %*
exit /b 0

:use_exe
if not exist "%EXE%" goto :none
start "" "%EXE%" %*
exit /b 0

:none
echo.
echo [ERRO] Nenhum Python 3.8+ com tkinter foi encontrado e o
echo        ReperIO.exe nao esta nesta pasta.
echo.
echo  Baixe o pacote pronto (com o .exe) na pagina de Releases do projeto,
echo  ou instale o Python 3 de https://www.python.org/downloads/
echo.
pause
exit /b 1

:: Testa um candidato: precisa existir, ser 3.8+ e importar tkinter.
:try
if defined PYEXE goto :eof
if not exist "%~1" goto :eof
"%~1" -I -c "import sys,tkinter; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 goto :eof
set "PYEXE=%~1"
goto :eof
