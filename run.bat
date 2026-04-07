@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul 2>&1

set "REPO_DIR=%~dp0"
set "VENV_DIR=%REPO_DIR%venv"
set "MARKER=%VENV_DIR%\.installed"
set "PYTHON=%VENV_DIR%\Scripts\python.exe"
set "PIP=%VENV_DIR%\Scripts\pip.exe"

title See-through: Single-image Layer Decomposition for Anime Characters

echo ========================================================================
echo  See-through: Single-image Layer Decomposition for Anime Characters
echo ========================================================================
echo.

:: ──────────────────────────────────────────────────────
:: Step 1: Find Python
:: ──────────────────────────────────────────────────────
echo [1/4] Checking Python...

set "SYS_PYTHON="
where python >nul 2>&1 && (
    for /f "delims=" %%i in ('where python') do (
        if not defined SYS_PYTHON set "SYS_PYTHON=%%i"
    )
)
if not defined SYS_PYTHON (
    where py >nul 2>&1 && (
        for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)"') do (
            if not defined SYS_PYTHON set "SYS_PYTHON=%%i"
        )
    )
)
if not defined SYS_PYTHON (
    echo.
    echo  ERROR: Python not found!
    echo  Please install Python 3.10+ from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check Python version >= 3.10
"!SYS_PYTHON!" -c "import sys; f=open('_pyver.tmp','w'); f.write(f'{sys.version_info.major}.{sys.version_info.minor}'); f.close()" 2>nul
if exist "_pyver.tmp" (
    set /p PY_VER=<_pyver.tmp
    del "_pyver.tmp"
) else (
    set "PY_VER=0.0"
)
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    if %%a LSS 3 goto :bad_version
    if %%a==3 if %%b LSS 10 goto :bad_version
)
echo        Found Python !PY_VER! at !SYS_PYTHON!
goto :check_venv

:bad_version
echo.
echo  ERROR: Python !PY_VER! is too old. Please install Python 3.10 or newer.
echo.
pause
exit /b 1

:: ──────────────────────────────────────────────────────
:: Step 2: Create venv if needed
:: ──────────────────────────────────────────────────────
:check_venv
echo [2/4] Checking virtual environment...

if not exist "%PYTHON%" (
    echo        Creating virtual environment...
    "!SYS_PYTHON!" -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo  ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo        Virtual environment created.
) else (
    echo        Virtual environment found.
)

:: ──────────────────────────────────────────────────────
:: Step 3: Install dependencies if needed
:: ──────────────────────────────────────────────────────
echo [3/4] Checking dependencies...

if exist "%MARKER%" (
    echo        Dependencies already installed.
    goto :check_gpu
)

echo.
echo  First-time setup: installing dependencies...
echo  This may take 10-20 minutes depending on your internet speed.
echo.

:: Install PyTorch with CUDA
echo  Installing PyTorch with CUDA support...
"%PIP%" install torch==2.8.0+cu128 torchvision==0.23.0+cu128 torchaudio==2.8.0+cu128 --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install PyTorch.
    pause
    exit /b 1
)

:: Install project dependencies
echo.
echo  Installing project dependencies...
cd /d "%REPO_DIR%"
"%PIP%" install -r requirements-portable.txt
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  If you see C++ compiler errors, install Visual Studio Build Tools:
    echo  https://visualstudio.microsoft.com/visual-cpp-build-tools/
    pause
    exit /b 1
)

:: Mark as installed
echo installed > "%MARKER%"
echo.
echo  Setup complete!
echo.

:: ──────────────────────────────────────────────────────
:: Step 4: Check GPU and launch
:: ──────────────────────────────────────────────────────
:check_gpu
echo [4/4] Checking GPU...

cd /d "%REPO_DIR%"
"%PYTHON%" -c "import torch,sys; ok=torch.cuda.is_available(); f=open('_gpu.tmp','w'); f.write(torch.cuda.get_device_name(0)+' (VRAM: '+str(round(torch.cuda.get_device_properties(0).total_memory/1024**3,1))+' GB)') if ok else f.write('NONE'); f.close()" 2>nul
set "GPU_OK=NONE"
if exist "%REPO_DIR%_gpu.tmp" (
    set /p GPU_OK=<"%REPO_DIR%_gpu.tmp"
    del "%REPO_DIR%_gpu.tmp"
)
if "!GPU_OK!"=="NONE" (
    echo.
    echo  WARNING: No NVIDIA GPU with CUDA detected!
    echo  This tool requires an NVIDIA GPU with at least 8 GB VRAM.
    echo  Make sure you have the latest NVIDIA drivers installed.
    echo.
    set /p CONTINUE="  Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
) else (
    echo        GPU: !GPU_OK!
)

echo.
echo ====================================================
echo  Starting Gradio UI...
echo  Loading models, please wait...
echo  (This may take 10-30 seconds on first load)
echo  Browser will open at http://127.0.0.1:7860
echo  Close this window to stop the server.
echo ====================================================
echo.

cd /d "%REPO_DIR%"
"%PYTHON%" app.py
pause
