# -*- coding: utf-8 -*-
"""
主窗口
"""
import sys
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout,
    QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from config.settings import Settings
from utils.logger import get_logger
from .register_tab import RegisterTab
from .monitor_tab import MonitorTab
from .accounts_tab import AccountsTab
from .data_management_tab import DataManagementTab

logger = get_logger(__name__)


class MainWindow(QMainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        # 设置窗口标题和大小
        self.setWindowTitle(f"{Settings.APP_NAME} v{Settings.APP_VERSION}")
        self.resize(Settings.WINDOW_WIDTH, Settings.WINDOW_HEIGHT)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 创建Tab控件
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 创建各个Tab
        self.register_tab = RegisterTab()
        self.monitor_tab = MonitorTab()
        self.accounts_tab = AccountsTab()
        self.data_management_tab = DataManagementTab()

        # 添加Tab
        self.tab_widget.addTab(self.register_tab, "📧 自动注册")
        self.tab_widget.addTab(self.monitor_tab, "📬 邮件监听")
        self.tab_widget.addTab(self.accounts_tab, "📋 账号管理")
        self.tab_widget.addTab(self.data_management_tab, "🗂️ 数据管理")
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")
        
        # 连接信号
        self.register_tab.status_updated.connect(self.update_status)
        self.monitor_tab.status_updated.connect(self.update_status)

        # 注册Tab的切换到监听信号
        self.register_tab.switch_to_monitor.connect(self.switch_to_monitor_tab)

        # 当切换到账号管理Tab时，刷新列表
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # 应用启动时加载账号列表
        self.register_tab.load_accounts()

        logger.info("主窗口初始化完成")
    
    def update_status(self, message):
        """更新状态栏"""
        self.status_bar.showMessage(message)
        logger.debug(f"状态更新: {message}")
    
    def switch_to_monitor_tab(self, email, password):
        """切换到监听Tab并填充信息"""
        # 切换到监听Tab
        self.tab_widget.setCurrentIndex(1)
        # 填充邮箱和密码
        self.monitor_tab.fill_account_info(email, password)
        self.update_status(f"切换到监听: {email}")

    def on_tab_changed(self, index):
        """Tab切换事件"""
        if index == 0:  # 注册Tab
            self.register_tab.load_accounts()
        elif index == 2:  # 账号管理Tab
            self.accounts_tab.refresh_accounts()
        elif index == 3:  # 数据管理Tab
            self.data_management_tab.load_all_data()

    def closeEvent(self, event):
        """关闭事件"""
        logger.info("用户关闭程序")
        event.accept()

