@echo off
rem Construye dist\GestorTerminologico.exe. Hay que ejecutarlo EN WINDOWS y con el
rem Python oficial de python.org (no el de MSYS2). Doble clic o desde la terminal.
chcp 65001 >nul

where py >nul 2>nul && (set PY=py -3) || (set PY=python)

echo [1/3] Instalando PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto error

echo [2/3] Pasando los tests...
%PY% -m unittest
if errorlevel 1 goto error

echo [3/3] Construyendo el programa...
%PY% -m PyInstaller --noconfirm --clean --onefile --name GestorTerminologico app_web.py
if errorlevel 1 goto error

echo.
echo Listo: dist\GestorTerminologico.exe
pause
exit /b 0

:error
echo.
echo Algo ha fallado. Lee los mensajes de arriba.
pause
exit /b 1