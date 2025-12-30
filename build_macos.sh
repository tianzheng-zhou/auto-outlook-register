#!/bin/bash
# macOS 打包脚本
# 使用 conda 环境打包

set -e

echo "=================================="
echo "  Outlook 自动注册工具 - macOS 打包"
echo "=================================="
echo ""

# 初始化 conda
eval "$(conda shell.bash hook)"

# 激活 tool 环境
echo "🔄 激活 conda tool 环境..."
conda activate tool

echo "✅ 当前 conda 环境: $CONDA_DEFAULT_ENV"
echo ""

# 检查依赖
echo "📦 检查依赖..."
pip list | grep -q PyInstaller || pip install PyInstaller
pip list | grep -q PyQt6 || pip install PyQt6

# 清理旧的构建文件
echo "🧹 清理旧的构建文件..."
rm -rf build dist *.app *.spec 2>/dev/null || true

# 运行 PyInstaller
echo "🔨 开始打包..."
pyinstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name OutlookRegister \
    --icon=app_icon.icns \
    --add-binary="config/chromedriver:config" \
    --hidden-import=PyQt6 \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWidgets \
    --hidden-import=selenium \
    --hidden-import=undetected_chromedriver \
    main.py

# 检查打包结果
if [ -d "dist/OutlookRegister.app" ]; then
    echo ""
    echo "✅ 打包成功！"
    echo "📦 应用位置: dist/OutlookRegister.app"
    echo ""
    echo "🚀 运行应用:"
    echo "   open dist/OutlookRegister.app"
    echo ""
else
    echo "❌ 打包失败！"
    exit 1
fi

