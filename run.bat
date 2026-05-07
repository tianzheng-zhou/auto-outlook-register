@echo off
REM Outlook 自动注册工具启动脚本 (Windows)
REM 自动使用项目内 .venv 虚拟环境，缺则创建，依赖缺则安装

setlocal
set "PROJECT_DIR=%~dp0"
set "VENV_DIR=%PROJECT_DIR%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
REM 强制 UTF-8 模式，避免 GBK 解码 requirements.txt 中文注释失败
set "PYTHONUTF8=1"
REM 国内 PyPI 镜像（如不需要可注释掉这一行）
set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"

echo ==================================
echo   Outlook 自动注册工具
echo ==================================
echo.

REM 1. 确保系统有 Python（仅在 .venv 不存在时需要）
if not exist "%VENV_PY%" (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] 未找到系统 Python，请先安装 Python 3.10+
        pause
        exit /b 1
    )

    echo [INFO] 未找到 .venv，正在创建虚拟环境...
    python -m venv "%VENV_DIR%"
    if errorlevel 1 (
        echo [ERROR] 创建虚拟环境失败
        pause
        exit /b 1
    )
)

REM 2. 检查依赖（PyQt6 作为标志）
"%VENV_PY%" -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [INFO] 缺少依赖，正在安装到 .venv ...
    "%VENV_PY%" -m pip install -r "%PROJECT_DIR%requirements.txt" --disable-pip-version-check
    if errorlevel 1 (
        echo [ERROR] 依赖安装失败
        pause
        exit /b 1
    )
)

REM 3. 启动应用
echo [INFO] 启动应用...
"%VENV_PY%" "%PROJECT_DIR%main.py"

echo.
echo 应用已关闭
pause
endlocal

