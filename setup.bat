@echo off
setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"

:: ── Python interpreter ────────────────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo Error: no Python interpreter found. Install Python 3.11+ and try again.
    exit /b 1
)

for /f "delims=" %%v in ('python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set "PYTHON_VERSION=%%v"
for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)"') do set "PYTHON_EXE=%%p"
echo Using Python %PYTHON_VERSION% at %PYTHON_EXE%

:: ── Virtual environment ───────────────────────────────────────────────────────
if exist "%VENV_DIR%\Scripts\activate.bat" (
    echo Virtual environment already exists at .venv -- skipping creation.
) else (
    echo Creating virtual environment at .venv ...
    python -m venv "%VENV_DIR%"
)

call "%VENV_DIR%\Scripts\activate.bat"

:: ── Core dependencies ─────────────────────────────────────────────────────────
echo.
echo Installing core requirements ...
pip install --quiet --upgrade pip
pip install --quiet -r "%SCRIPT_DIR%requirements.txt"
echo Core requirements installed.

:: ── Optional dependencies ─────────────────────────────────────────────────────
echo.
set /p "ANSWER=Install optional dependencies (ChromaDB / semantic search)? [y/N] "
if /i "%ANSWER%"=="y" (
    echo Installing optional requirements ...
    pip install --quiet -r "%SCRIPT_DIR%requirements-optional.txt"
    echo Optional requirements installed.
) else (
    echo Skipping optional requirements.
)

echo.
echo Setup complete. Run run.bat to start the application.
endlocal
