@echo off
REM Outlook 自动注册工具启动脚本 (Windows)

echo ==================================
echo   Outlook 自动注册工具
echo ==================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 检查依赖
echo 📦 检查依赖...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  缺少依赖，正在安装...
    pip install -r requirements.txt
)

REM 启动应用
echo 🚀 启动应用...
python main.py

echo.
echo 👋 应用已关闭
pause

