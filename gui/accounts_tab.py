# -*- coding: utf-8 -*-
"""
账号管理功能Tab
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QLabel, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from utils.file_manager import FileManager
from utils.logger import get_logger
from config.settings import Settings

logger = get_logger(__name__)


class AccountsTab(QWidget):
    """账号管理Tab"""
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.accounts = []
        self.init_ui()
        self.refresh_accounts()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # === 统计信息 ===
        stats_group = QGroupBox("统计信息")
        stats_layout = QHBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.total_label = QLabel("总数: 0")
        self.registered_label = QLabel("已注册: 0")
        self.unregistered_label = QLabel("未注册: 0")
        
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.registered_label)
        stats_layout.addWidget(self.unregistered_label)
        stats_layout.addStretch()
        
        layout.addWidget(stats_group)
        
        # === 账号列表 ===
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["状态", "邮箱", "密码", "生日", "创建时间"])
        
        # 设置列宽
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置表格属性
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # === 操作按钮 ===
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_accounts)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        export_btn = QPushButton("📤 导出")
        export_btn.clicked.connect(self.export_accounts)
        export_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        copy_btn = QPushButton("📋 复制选中")
        copy_btn.clicked.connect(self.copy_selected)
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.clicked.connect(self.clear_accounts)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(export_btn)
        button_layout.addWidget(copy_btn)
        button_layout.addStretch()
        button_layout.addWidget(clear_btn)
        
        layout.addLayout(button_layout)
    
    def refresh_accounts(self):
        """刷新账号列表"""
        logger.info("刷新账号列表")
        self.accounts = FileManager.load_accounts()
        self.update_table()
        self.update_stats()
        self.status_updated.emit(f"已加载 {len(self.accounts)} 个账号")
    
    def update_table(self):
        """更新表格"""
        self.table.setRowCount(len(self.accounts))
        
        for i, account in enumerate(self.accounts):
            # 状态
            status = account.get('status', '未知')
            status_item = QTableWidgetItem(status)
            if status == '已注册':
                status_item.setBackground(QColor(76, 175, 80, 50))  # 绿色
            else:
                status_item.setBackground(QColor(255, 152, 0, 50))  # 橙色
            self.table.setItem(i, 0, status_item)
            
            # 邮箱
            self.table.setItem(i, 1, QTableWidgetItem(account.get('email', '')))
            
            # 密码
            self.table.setItem(i, 2, QTableWidgetItem(account.get('password', '')))
            
            # 生日
            self.table.setItem(i, 3, QTableWidgetItem(account.get('birthday', '')))
            
            # 创建时间
            self.table.setItem(i, 4, QTableWidgetItem(account.get('created_at', '')))
    
    def update_stats(self):
        """更新统计信息"""
        total = len(self.accounts)
        registered = sum(1 for acc in self.accounts if acc.get('status') == '已注册')
        unregistered = total - registered
        
        self.total_label.setText(f"总数: {total}")
        self.registered_label.setText(f"已注册: {registered}")
        self.unregistered_label.setText(f"未注册: {unregistered}")
    
    def export_accounts(self):
        """导出账号"""
        if not self.accounts:
            QMessageBox.warning(self, "警告", "没有可导出的账号！")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出账号",
            "outlook_accounts_export.txt",
            "文本文件 (*.txt);;所有文件 (*)"
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy(Settings.ACCOUNTS_FILE, file_path)
                QMessageBox.information(self, "成功", f"账号已导出到:\n{file_path}")
                logger.info(f"账号已导出到: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败:\n{str(e)}")
                logger.error(f"导出失败: {e}")
    
    def copy_selected(self):
        """复制选中的账号"""
        selected_rows = set(item.row() for item in self.table.selectedItems())
        
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要复制的账号！")
            return
        
        # 构建复制文本
        text_lines = []
        for row in sorted(selected_rows):
            account = self.accounts[row]
            text_lines.append(f"邮箱: {account.get('email', '')}")
            text_lines.append(f"密码: {account.get('password', '')}")
            text_lines.append(f"生日: {account.get('birthday', '')}")
            text_lines.append(f"状态: {account.get('status', '')}")
            text_lines.append("-" * 50)
        
        # 复制到剪贴板
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(text_lines))
        
        QMessageBox.information(self, "成功", f"已复制 {len(selected_rows)} 个账号到剪贴板！")
    
    def clear_accounts(self):
        """清空账号"""
        if not self.accounts:
            QMessageBox.warning(self, "警告", "账号列表已经是空的！")
            return
        
        reply = QMessageBox.question(
            self,
            '确认清空',
            f'确定要清空所有 {len(self.accounts)} 个账号吗？\n\n此操作不可恢复！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 清空文件
                Settings.ACCOUNTS_FILE.write_text('', encoding='utf-8')
                self.refresh_accounts()
                QMessageBox.information(self, "成功", "账号列表已清空！")
                logger.info("账号列表已清空")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"清空失败:\n{str(e)}")
                logger.error(f"清空失败: {e}")

