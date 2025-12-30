# Outlook 邮箱自动注册工具

## 📋 功能说明

用于**功能测试**的 Outlook 邮箱自动注册工具，使用 `undetected-chromedriver` 绕过反检测。

## ✨ 核心特性

- ✅ **智能反检测**：使用 undetected-chromedriver 绕过 PerimeterX 验证
- ✅ **随机邮箱生成**：无规律前缀（6-10位字母数字混合）
- ✅ **随机密码生成**：符合 Outlook 强密码要求
- ✅ **GUI 界面**：PyQt6 友好的用户界面
- ✅ **邮件监听**：支持浏览器和 API 两种模式
- ✅ **账号管理**：统一管理注册的账号

## 📦 快速开始

### 1. 环境要求

- **Python**: 3.8+
- **Chrome**: 142+ （推荐最新版）
- **操作系统**: macOS / Windows
- **Conda**: 用于环境隔离（推荐）

### 2. 创建 Conda 环境

```bash
# 创建 conda 环境
conda create -n tool python=3.10

# 激活环境
conda activate tool
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖说明**：
- `selenium>=4.0.0` - Web 自动化框架
- `undetected-chromedriver>=3.5.0` - 绕过反检测（✅ **核心依赖**）
- `PyQt6>=6.0.0` - GUI 框架

### 4. 运行脚本

```bash
# 开发模式运行
python main.py
```

### 5. 查看结果

账号信息保存在 `data/accounts.txt`，格式如下：

```
状态: 已注册
邮箱: k7m9x2a@outlook.com
密码: Xy9#mK2p
生日: 1995-3-15
创建时间: 2025-10-30 10:30:45
--------------------------------------------------
```

## 🔨 打包成可执行应用

### ⚠️ 重要：PyInstaller 打包问题修复

**问题**：打包后的应用会无限循环启动，直到系统卡死

**原因**：PyInstaller 在打包时会重新导入主模块，导致 `if __name__ == "__main__"` 保护失效

**解决方案**：已在 `main.py` 中添加 `multiprocessing.freeze_support()` 保护

### macOS 打包

```bash
# 直接运行打包脚本（会自动激活 tool 环境）
bash build_macos.sh
```

**打包完成后**：
- 应用位置：`dist/OutlookRegister.app`
- 运行应用：`open dist/OutlookRegister.app`

### Windows 打包

```bash
# 直接运行打包脚本（会自动激活 tool 环境）
build_windows.bat
```

**打包完成后**：
- 应用位置：`dist\OutlookRegister.exe`
- 运行应用：`dist\OutlookRegister.exe`

### 打包脚本说明

打包脚本会自动：
1. ✅ 激活 conda tool 环境
2. ✅ 检查并安装必要的依赖
3. ✅ 清理旧的构建文件
4. ✅ 使用 PyInstaller 打包应用
5. ✅ 验证打包结果

**打包参数**：
- `--onefile`：单个可执行文件
- `--windowed`：GUI 应用（无控制台窗口）
- `--icon`：应用图标（macOS 使用 .icns，Windows 使用 .ico）
- `--hidden-import`：隐藏导入（确保所有依赖被打包）

### 打包后的应用特性

✅ **单文件可执行**：无需 Python 环境
✅ **跨平台**：macOS 和 Windows 都支持
✅ **无限循环修复**：已解决 PyInstaller 打包问题
✅ **完整功能**：所有 GUI 功能都可用
✅ **自动依赖**：所有依赖都已打包
✅ **应用图标**：macOS 和 Windows 都有图标显示
✅ **数据持久化**：账号信息正确保存和加载（支持打包后的应用）
✅ **智能数据存储**：自动在用户目录创建数据文件夹，无权限问题

### 数据文件存储位置

打包后的应用会自动在以下位置创建数据文件夹：

- **macOS**: `~/Library/Application Support/OutlookRegister/`
- **Windows**: `%APPDATA%\OutlookRegister\`
- **Linux**: `~/.config/OutlookRegister/`

数据文件包括：
- `data/accounts.txt` - 注册的账号信息
- `data/tokens/` - API token 文件
- `data/account_logs/` - 账号注册日志
- `logs/app.log` - 应用日志

### 常见打包问题

#### Q: 打包脚本找不到 build_app.spec？

**解决方法**：
- 打包脚本已改为直接使用 PyInstaller 命令行参数，无需 spec 文件
- 脚本会自动清理旧的 spec 文件

#### Q: 打包后应用启动很慢？

**原因**：第一次启动需要解压所有依赖

**解决方法**：
- 这是正常现象，第一次启动会比较慢（可能需要 10-30 秒）
- 后续启动会快一些

#### Q: 点击"开始监听"按钮闪退或报错？

**原因**：可能是以下几个原因：
1. Chrome 浏览器未安装
2. 数据目录权限问题
3. 其他初始化错误

**解决方法**：
1. 确保已安装 Google Chrome 浏览器
2. 查看日志文件获取具体错误信息：
   - **macOS**: `~/Library/Application Support/OutlookRegister/logs/app.log`
   - **Windows**: `%APPDATA%\OutlookRegister\logs\app.log`
3. 应用会自动在用户目录创建数据文件夹，无需手动配置



## 📚 项目结构

```
auto-outlook-register/
├── main.py                      # 主入口（已修复 PyInstaller 问题）
├── requirements.txt             # 依赖列表
├── README.md                    # 本文档
├── build_macos.sh              # macOS 打包脚本
├── build_windows.bat           # Windows 打包脚本
├── run.sh                       # macOS 运行脚本
├── run.bat                      # Windows 运行脚本
│
├── config/                      # 配置模块
│   ├── __init__.py
│   └── settings.py             # 应用配置
│
├── core/                        # 核心业务逻辑
│   ├── __init__.py
│   ├── outlook_register.py     # 注册逻辑
│   ├── outlook_monitor.py      # 邮件监听（浏览器模式）
│   ├── outlook_api_monitor.py  # 邮件监听（API模式）
│   ├── email_imap.py           # IMAP 邮件获取
│   └── token_manager.py        # Token 管理
│
├── gui/                         # GUI 模块
│   ├── __init__.py
│   ├── main_window.py          # 主窗口
│   ├── register_tab.py         # 注册 Tab
│   ├── monitor_tab.py          # 监听 Tab
│   └── accounts_tab.py         # 账号管理 Tab
│
├── utils/                       # 工具模块
│   ├── __init__.py
│   ├── logger.py               # 日志系统
│   ├── file_manager.py         # 文件管理
│   └── log_manager.py          # 日志管理
│
├── data/                        # 数据目录（自动生成）
│   ├── accounts.txt            # 账号信息
│   ├── account_logs/           # 账号日志
│   └── tokens/                 # API Token
│
├── logs/                        # 日志目录（自动生成）
│   └── app.log                 # 应用日志
│
├── dist/                        # 打包输出目录
│   ├── OutlookRegister.app     # macOS 应用
│   └── OutlookRegister.exe     # Windows 应用
│
└── build/                       # PyInstaller 构建目录
```



---

**最后更新**: 2025-10-30
**版本**: v4.0
**作者**: IoT Util Team

## 🔄 版本更新日志

### v4.0 (2025-10-30) - PyInstaller 打包修复版本

✅ **新增功能**：
- 添加 PyInstaller 打包支持（macOS 和 Windows）
- 创建 `build_app.spec` 打包配置文件
- 创建 `build_macos.sh` 和 `build_windows.bat` 打包脚本
- 添加详细的打包文档和常见问题解答

🔧 **关键修复**：
- **修复 PyInstaller 无限循环启动问题**：在 `main.py` 中添加 `multiprocessing.freeze_support()`
- 确保 `if __name__ == "__main__"` 保护正确生效
- 添加隐藏导入配置，确保所有依赖都被打包

📚 **文档更新**：
- 添加完整的打包指南（macOS 和 Windows）
- 添加打包常见问题解答
- 更新项目结构说明
- 添加打包后应用特性说明

### v3.0 - GUI 版本

✅ 完整的 PyQt6 GUI 界面
✅ 三个 Tab：注册、监听、账号管理
✅ 支持浏览器和 API 两种监听模式
✅ 完整的日志和截图功能
