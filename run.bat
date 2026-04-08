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
:: Step 1: Find compatible Python (3.10 - 3.12)
:: ──────────────────────────────────────────────────────
echo [1/4] Checking Python...

set "SYS_PYTHON="

:: Try py launcher first (supports version selection)
where py >nul 2>&1 && (
    for %%v in (3.12 3.11 3.10) do (
        if not defined SYS_PYTHON (
            py -%%v -c "import sys; print(sys.executable)" >_pyexe.tmp 2>nul
            if not errorlevel 1 (
                set /p SYS_PYTHON=<_pyexe.tmp
            )
            if exist "_pyexe.tmp" del "_pyexe.tmp"
        )
    )
)

:: Fallback: check PATH python
if not defined SYS_PYTHON (
    where python >nul 2>&1 && (
        for /f "delims=" %%i in ('where python') do (
            if not defined SYS_PYTHON set "SYS_PYTHON=%%i"
        )
    )
)

:: If no compatible Python found, try auto-install via winget
if not defined SYS_PYTHON goto :try_auto_install

:: Verify version is 3.10 - 3.12
"!SYS_PYTHON!" -c "import sys; f=open('_pyver.tmp','w'); f.write(f'{sys.version_info.major}.{sys.version_info.minor}'); f.close()" 2>nul
if exist "_pyver.tmp" (
    set /p PY_VER=<_pyver.tmp
    del "_pyver.tmp"
) else (
    set "PY_VER=0.0"
)
for /f "tokens=1,2 delims=." %%a in ("!PY_VER!") do (
    if %%a LSS 3 goto :try_auto_install
    if %%a==3 if %%b LSS 10 goto :try_auto_install
    if %%a==3 if %%b GTR 12 goto :try_auto_install
)
echo        Found Python !PY_VER! at !SYS_PYTHON!
goto :check_venv

:try_auto_install
echo.
echo  No compatible Python (3.10 - 3.12) found.
echo  Attempting to install Python 3.12 via winget...
echo.
where winget >nul 2>&1
if errorlevel 1 (
    echo  ERROR: winget not available. Please install Python 3.12 manually:
    echo  https://www.python.org/downloads/release/python-3129/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
winget install Python.Python.3.12 --silent --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install Python via winget.
    echo  Please install Python 3.12 manually:
    echo  https://www.python.org/downloads/release/python-3129/
    echo  Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)
echo.
echo  Python 3.12 installed successfully!
echo  Please close this window and double-click run.bat again.
echo.
pause
exit /b 0

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
"%PIP%" install torch==2.8.0+cu126 torchvision==0.23.0+cu126 torchaudio==2.8.0+cu126 --index-url https://download.pytorch.org/whl/cu126
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

:: Check NVIDIA driver version (CUDA 12.6 requires >= 560)
set "DRIVER_VER="
for /f "delims=" %%i in ('nvidia-smi --query-gpu=driver_version --format^=csv^,noheader 2^>nul') do (
    if not defined DRIVER_VER set "DRIVER_VER=%%i"
)
if not defined DRIVER_VER (
    echo.
    echo  WARNING: NVIDIA driver not detected!
    echo  This tool requires an NVIDIA GPU with at least 8 GB VRAM.
    echo  Please install the latest NVIDIA driver:
    echo  https://www.nvidia.com/download/index.aspx
    echo.
    set /p CONTINUE="  Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
    goto :skip_driver_check
)
:: Check driver >= 560
for /f "tokens=1 delims=." %%a in ("!DRIVER_VER!") do (
    if %%a LSS 560 (
        echo.
        echo  WARNING: NVIDIA driver !DRIVER_VER! is too old for CUDA 12.6.
        echo  Please update to the latest driver:
        echo  https://www.nvidia.com/download/index.aspx
        echo.
        set /p CONTINUE="  Continue anyway? (y/N): "
        if /i not "!CONTINUE!"=="y" exit /b 1
    )
)
:skip_driver_check

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
    echo  If you have an NVIDIA GPU, please update your driver:
    echo  https://www.nvidia.com/download/index.aspx
    echo.
    set /p CONTINUE="  Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
) else (
    echo        GPU: !GPU_OK! ^(Driver: !DRIVER_VER!^)
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

:: Release directory handles so workspace can be deleted
cd /d "%USERPROFILE%"
pause
