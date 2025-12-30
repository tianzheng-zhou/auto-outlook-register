# -*- coding: utf-8 -*-
"""
数据管理Tab页
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGridLayout,
    QTableWidget, QTableWidgetItem, QPushButton, QLabel,
    QLineEdit, QTextEdit, QComboBox, QSpinBox, QMessageBox,
    QHeaderView, QGroupBox, QFormLayout, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from database import DatabaseManager, Email, User, Card
from utils.email_generator import EmailGenerator
from utils.user_generator import UserGenerator
from utils.card_generator import CardGenerator
from utils.logger import logger
from gui.augment_tab import AugmentTab


class DataManagementTab(QWidget):
    """数据管理Tab页"""

    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.init_ui()
        self.load_all_data()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()

        # 创建子Tab
        self.sub_tabs = QTabWidget()
        self.sub_tabs.addTab(AugmentTab(), "🎯 Augment")
        self.sub_tabs.addTab(self.create_email_tab(), "📧 邮箱管理")
        self.sub_tabs.addTab(self.create_user_tab(), "👤 用户信息")
        self.sub_tabs.addTab(self.create_card_tab(), "💳 卡片信息")

        layout.addWidget(self.sub_tabs)
        self.setLayout(layout)

    # ==================== 邮箱管理 ====================

    def create_email_tab(self):
        """创建邮箱管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 顶部：生成器（双列布局）
        generator_group = QGroupBox("邮箱生成器")
        generator_layout = QGridLayout()

        # 第一行：生成模式（跨两列）
        generator_layout.addWidget(QLabel("生成模式:"), 0, 0)
        self.email_mode_combo = QComboBox()
        self.email_mode_combo.addItems(["顺序生成", "随机生成", "固定邮箱"])
        self.email_mode_combo.currentTextChanged.connect(self.on_email_mode_changed)
        generator_layout.addWidget(self.email_mode_combo, 0, 1, 1, 3)

        # 第二行：前缀 | 后缀
        generator_layout.addWidget(QLabel("前缀:"), 1, 0)
        self.email_prefix_input = QLineEdit()
        self.email_prefix_input.setPlaceholderText("例如: chat")
        generator_layout.addWidget(self.email_prefix_input, 1, 1)

        generator_layout.addWidget(QLabel("后缀:"), 1, 2)
        self.email_suffix_input = QLineEdit()
        self.email_suffix_input.setPlaceholderText("例如: @outlook.com")
        generator_layout.addWidget(self.email_suffix_input, 1, 3)

        # 第三行：数量 | 起始数字
        generator_layout.addWidget(QLabel("数量:"), 2, 0)
        self.email_count_spin = QSpinBox()
        self.email_count_spin.setRange(1, 1000)
        self.email_count_spin.setValue(10)
        generator_layout.addWidget(self.email_count_spin, 2, 1)

        self.email_start_label = QLabel("起始数字:")
        generator_layout.addWidget(self.email_start_label, 2, 2)
        self.email_start_spin = QSpinBox()
        self.email_start_spin.setRange(1, 99999)
        self.email_start_spin.setValue(1)
        generator_layout.addWidget(self.email_start_spin, 2, 3)

        # 第四行：固定邮箱列表（跨所有列）
        self.email_fixed_label = QLabel("邮箱列表:")
        self.email_fixed_label.hide()
        generator_layout.addWidget(self.email_fixed_label, 3, 0)
        self.email_fixed_text = QTextEdit()
        self.email_fixed_text.setPlaceholderText("每行一个邮箱\n例如:\ntest1@outlook.com\ntest2@outlook.com")
        self.email_fixed_text.setMaximumHeight(80)
        self.email_fixed_text.hide()
        generator_layout.addWidget(self.email_fixed_text, 3, 1, 1, 3)

        # 第五行：按钮
        btn_layout = QHBoxLayout()
        self.email_generate_btn = QPushButton("🚀 生成邮箱")
        self.email_generate_btn.clicked.connect(self.generate_emails)
        self.email_clear_btn = QPushButton("🗑️ 清空列表")
        self.email_clear_btn.clicked.connect(self.clear_emails)
        self.import_outlook_btn = QPushButton("📧 导入Outlook邮箱")
        self.import_outlook_btn.clicked.connect(self.import_outlook_accounts)
        btn_layout.addWidget(self.email_generate_btn)
        btn_layout.addWidget(self.email_clear_btn)
        btn_layout.addWidget(self.import_outlook_btn)
        btn_layout.addStretch()
        generator_layout.addLayout(btn_layout, 4, 0, 1, 4)

        generator_group.setLayout(generator_layout)
        layout.addWidget(generator_group)

        # 底部：邮箱列表
        list_group = QGroupBox("邮箱列表")
        list_layout = QVBoxLayout()

        # 统计信息
        self.email_stats_label = QLabel("总数: 0 | 未使用: 0 | 已使用: 0")
        self.email_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        list_layout.addWidget(self.email_stats_label)

        # 表格
        self.email_table = QTableWidget()
        self.email_table.setColumnCount(5)
        self.email_table.setHorizontalHeaderLabels(["ID", "邮箱", "类型", "状态", "创建时间"])
        self.email_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.email_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.email_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        list_layout.addWidget(self.email_table)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.email_delete_btn = QPushButton("删除选中")
        self.email_delete_btn.clicked.connect(self.delete_selected_emails)
        self.email_refresh_btn = QPushButton("刷新")
        self.email_refresh_btn.clicked.connect(self.load_emails)
        action_layout.addWidget(self.email_delete_btn)
        action_layout.addWidget(self.email_refresh_btn)
        action_layout.addStretch()
        list_layout.addLayout(action_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        widget.setLayout(layout)
        return widget

    def on_email_mode_changed(self, mode: str):
        """邮箱生成模式改变"""
        if mode == "固定邮箱":
            self.email_prefix_input.hide()
            self.email_suffix_input.hide()
            self.email_count_spin.hide()
            self.email_start_label.hide()
            self.email_start_spin.hide()
            self.email_fixed_label.show()
            self.email_fixed_text.show()
        else:
            self.email_prefix_input.show()
            self.email_suffix_input.show()
            self.email_count_spin.show()
            self.email_fixed_label.hide()
            self.email_fixed_text.hide()

            if mode == "顺序生成":
                self.email_start_label.show()
                self.email_start_spin.show()
            else:
                self.email_start_label.hide()
                self.email_start_spin.hide()

    def generate_emails(self):
        """生成邮箱"""
        try:
            mode = self.email_mode_combo.currentText()

            if mode == "固定邮箱":
                # 解析固定邮箱
                email_string = self.email_fixed_text.toPlainText()
                if not email_string.strip():
                    QMessageBox.warning(self, "警告", "请输入邮箱列表！")
                    return

                emails = EmailGenerator.parse_fixed_emails(email_string)
            else:
                prefix = self.email_prefix_input.text().strip()
                suffix = self.email_suffix_input.text().strip()
                count = self.email_count_spin.value()

                if not prefix or not suffix:
                    QMessageBox.warning(self, "警告", "请输入前缀和后缀！")
                    return

                if mode == "顺序生成":
                    start_number = self.email_start_spin.value()
                    emails = EmailGenerator.generate_emails_sequence(prefix, suffix, count, start_number)
                else:  # 随机生成
                    emails = EmailGenerator.generate_emails_random(prefix, suffix, count)

            # 保存到数据库
            count = self.db.add_emails_batch(emails)
            QMessageBox.information(self, "成功", f"成功生成 {count} 个邮箱！")
            self.load_emails()

        except Exception as e:
            logger.error(f"生成邮箱失败: {e}")
            QMessageBox.critical(self, "错误", f"生成邮箱失败: {e}")

    def load_emails(self):
        """加载邮箱列表"""
        try:
            emails = self.db.get_all_emails()
            self.email_table.setRowCount(len(emails))

            for row, email in enumerate(emails):
                self.email_table.setItem(row, 0, QTableWidgetItem(str(email.id)))
                self.email_table.setItem(row, 1, QTableWidgetItem(email.email))
                self.email_table.setItem(row, 2, QTableWidgetItem(email.type))
                self.email_table.setItem(row, 3, QTableWidgetItem(email.status))
                self.email_table.setItem(row, 4, QTableWidgetItem(email.created_at))

            # 更新统计
            total = len(emails)
            unused = self.db.get_email_count('unused')
            used = self.db.get_email_count('used')
            self.email_stats_label.setText(f"总数: {total} | 未使用: {unused} | 已使用: {used}")

        except Exception as e:
            logger.error(f"加载邮箱失败: {e}")

    def delete_selected_emails(self):
        """删除选中的邮箱"""
        selected_rows = self.email_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的邮箱！")
            return

        try:
            for row in selected_rows:
                email_id = int(self.email_table.item(row.row(), 0).text())
                self.db.delete_email(email_id)
            self.load_emails()
        except Exception as e:
            logger.error(f"删除邮箱失败: {e}")
            QMessageBox.critical(self, "错误", f"删除失败: {e}")



    def clear_emails(self):
        """清空邮箱列表"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有邮箱吗？此操作不可恢复！")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                emails = self.db.get_all_emails()
                for email in emails:
                    self.db.delete_email(email.id)

                QMessageBox.information(self, "成功", "清空成功！")
                self.load_emails()
            except Exception as e:
                logger.error(f"清空邮箱失败: {e}")
                QMessageBox.critical(self, "错误", f"清空失败: {e}")

    
    def import_outlook_accounts(self):
        """一键导入 Outlook 账号到 Augment 邮箱列表"""
        try:
            # 获取所有已注册的 Outlook 账号
            outlook_accounts = self.db.get_all_outlook_accounts(status='registered')

            if not outlook_accounts:
                QMessageBox.warning(self, "警告", "没有已注册的 Outlook 账号！")
                return

            # 显示导入进度对话框
            progress = QMessageBox()
            progress.setWindowTitle("导入中...")
            progress.setText(f"正在导入 {len(outlook_accounts)} 个 Outlook 账号到邮箱列表...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()

            success_count = 0
            failed_count = 0

            for account in outlook_accounts:
                try:
                    email = account.get('email', '')

                    # 检查邮箱是否已存在
                    existing = self.db.get_email_by_id(email)
                    if existing:
                        logger.warning(f"邮箱已存在，跳过: {email}")
                        continue

                    # 添加到邮箱列表
                    from database.models import Email
                    import time
                    new_email = Email(
                        email=email,
                        type='imported',
                        status='unused',
                        created_at=time.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    self.db.add_email(new_email)
                    success_count += 1
                    logger.info(f"✅ 导入成功: {email}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ 导入失败: {email} - {e}")

            progress.close()

            # 显示导入结果
            msg = f"导入完成！\n\n成功: {success_count}\n失败: {failed_count}\n总计: {len(outlook_accounts)}"
            QMessageBox.information(self, "导入完成", msg)

            # 刷新邮箱列表
            self.load_emails()

        except Exception as e:
            logger.error(f"导入 Outlook 账号失败: {e}")
            QMessageBox.critical(self, "错误", f"导入失败: {e}")

    # ==================== 用户管理 ====================

    def create_user_tab(self):
        """创建用户管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 顶部：生成器（双列布局）
        generator_group = QGroupBox("用户信息生成器")
        generator_layout = QGridLayout()

        # 设置列宽比例：label窄，输入框宽
        generator_layout.setColumnStretch(0, 0)  # label列不拉伸
        generator_layout.setColumnStretch(1, 3)  # 第一个输入框
        generator_layout.setColumnStretch(2, 0)  # label列不拉伸
        generator_layout.setColumnStretch(3, 1)  # 第二个输入框（数量较窄）

        # 第一行：生成模式 | 数量
        generator_layout.addWidget(QLabel("生成模式:"), 0, 0)
        self.user_mode_combo = QComboBox()
        self.user_mode_combo.addItems(["随机生成", "手动输入"])
        self.user_mode_combo.currentTextChanged.connect(self.on_user_mode_changed)
        generator_layout.addWidget(self.user_mode_combo, 0, 1)

        self.user_count_label = QLabel("数量:")
        generator_layout.addWidget(self.user_count_label, 0, 2)
        self.user_count_spin = QSpinBox()
        self.user_count_spin.setRange(1, 1000)
        self.user_count_spin.setValue(10)
        generator_layout.addWidget(self.user_count_spin, 0, 3)

        # 第二行：手动输入框（跨所有列）
        self.user_manual_label = QLabel("用户信息:")
        self.user_manual_label.hide()
        generator_layout.addWidget(self.user_manual_label, 1, 0, Qt.AlignmentFlag.AlignTop)
        self.user_manual_text = QTextEdit()
        self.user_manual_text.setPlaceholderText(
            "格式示例：\n"
            "全名：劉思敏\n"
            "郵遞區號：110\n"
            "縣：台北市\n"
            "地區：信義區\n"
            "地址第 1 行：市府路7號\n"
            "地址第 2 行：（選填）\n"
            "\n"
            "多个用户用空行分隔"
        )
        self.user_manual_text.setMaximumHeight(100)
        self.user_manual_text.hide()
        generator_layout.addWidget(self.user_manual_text, 1, 1, 1, 3)

        # 第三行：按钮
        btn_layout = QHBoxLayout()
        self.user_generate_btn = QPushButton("🚀 生成用户")
        self.user_generate_btn.clicked.connect(self.generate_users)
        self.user_clear_btn = QPushButton("🗑️ 清空列表")
        self.user_clear_btn.clicked.connect(self.clear_users)
        btn_layout.addWidget(self.user_generate_btn)
        btn_layout.addWidget(self.user_clear_btn)
        btn_layout.addStretch()
        generator_layout.addLayout(btn_layout, 2, 0, 1, 4)

        generator_group.setLayout(generator_layout)
        layout.addWidget(generator_group)

        # 底部：用户列表
        list_group = QGroupBox("用户列表")
        list_layout = QVBoxLayout()

        # 统计信息
        self.user_stats_label = QLabel("总数: 0 | 未使用: 0 | 已使用: 0")
        self.user_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        list_layout.addWidget(self.user_stats_label)

        # 表格
        self.user_table = QTableWidget()
        self.user_table.setColumnCount(8)
        self.user_table.setHorizontalHeaderLabels(["ID", "姓名", "邮编", "县", "地区", "地址", "电话", "状态"])
        self.user_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.user_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.user_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.user_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        list_layout.addWidget(self.user_table)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.user_delete_btn = QPushButton("删除选中")
        self.user_delete_btn.clicked.connect(self.delete_selected_users)
        self.user_refresh_btn = QPushButton("刷新")
        self.user_refresh_btn.clicked.connect(self.load_users)
        action_layout.addWidget(self.user_delete_btn)
        action_layout.addWidget(self.user_refresh_btn)
        action_layout.addStretch()
        list_layout.addLayout(action_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        widget.setLayout(layout)
        return widget

    def on_user_mode_changed(self, mode: str):
        """用户生成模式改变"""
        if mode == "手动输入":
            self.user_count_label.hide()
            self.user_count_spin.hide()
            self.user_manual_label.show()
            self.user_manual_text.show()
        else:
            self.user_count_label.show()
            self.user_count_spin.show()
            self.user_manual_label.hide()
            self.user_manual_text.hide()

    def generate_users(self):
        """生成用户"""
        try:
            mode = self.user_mode_combo.currentText()

            if mode == "手动输入":
                # 解析手动输入
                user_string = self.user_manual_text.toPlainText()
                if not user_string.strip():
                    QMessageBox.warning(self, "警告", "请输入用户信息！")
                    return

                users = UserGenerator.parse_user_string(user_string)
            else:  # 随机生成
                count = self.user_count_spin.value()
                users = UserGenerator.generate_users(count, use_taiwan=True)

            # 保存到数据库
            count = self.db.add_users_batch(users)
            QMessageBox.information(self, "成功", f"成功生成 {count} 个用户！")
            self.load_users()

        except Exception as e:
            logger.error(f"生成用户失败: {e}")
            QMessageBox.critical(self, "错误", f"生成用户失败: {e}")

    def load_users(self):
        """加载用户列表"""
        try:
            users = self.db.get_all_users()
            self.user_table.setRowCount(len(users))

            for row, user in enumerate(users):
                self.user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                self.user_table.setItem(row, 1, QTableWidgetItem(user.full_name))
                self.user_table.setItem(row, 2, QTableWidgetItem(user.postal_code))
                self.user_table.setItem(row, 3, QTableWidgetItem(user.county))
                self.user_table.setItem(row, 4, QTableWidgetItem(user.district))
                self.user_table.setItem(row, 5, QTableWidgetItem(user.address_line1))
                self.user_table.setItem(row, 6, QTableWidgetItem(user.phone))
                self.user_table.setItem(row, 7, QTableWidgetItem(user.status))

            # 更新统计
            total = len(users)
            unused = self.db.get_user_count('unused')
            used = self.db.get_user_count('used')
            self.user_stats_label.setText(f"总数: {total} | 未使用: {unused} | 已使用: {used}")

        except Exception as e:
            logger.error(f"加载用户失败: {e}")

    def delete_selected_users(self):
        """删除选中的用户"""
        selected_rows = self.user_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的用户！")
            return

        reply = QMessageBox.question(self, "确认", f"确定要删除选中的 {len(selected_rows)} 个用户吗？")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for row in selected_rows:
                    user_id = int(self.user_table.item(row.row(), 0).text())
                    self.db.delete_user(user_id)

                QMessageBox.information(self, "成功", "删除成功！")
                self.load_users()
            except Exception as e:
                logger.error(f"删除用户失败: {e}")
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def clear_users(self):
        """清空用户列表"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有用户吗？此操作不可恢复！")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                users = self.db.get_all_users()
                for user in users:
                    self.db.delete_user(user.id)

                QMessageBox.information(self, "成功", "清空成功！")
                self.load_users()
            except Exception as e:
                logger.error(f"清空用户失败: {e}")
                QMessageBox.critical(self, "错误", f"清空失败: {e}")

    # ==================== 卡片管理 ====================

    def create_card_tab(self):
        """创建卡片管理Tab"""
        widget = QWidget()
        layout = QVBoxLayout()

        # 顶部：生成器（双列布局）
        generator_group = QGroupBox("卡片生成器")
        generator_layout = QGridLayout()

        # 设置列宽比例
        generator_layout.setColumnStretch(0, 0)  # label列不拉伸
        generator_layout.setColumnStretch(1, 2)  # 第一个输入框
        generator_layout.setColumnStretch(2, 0)  # label列不拉伸
        generator_layout.setColumnStretch(3, 1)  # 第二个输入框（数量较窄）

        # 第一行：生成模式（跨两列）
        generator_layout.addWidget(QLabel("生成模式:"), 0, 0)
        self.card_mode_combo = QComboBox()
        self.card_mode_combo.addItems(["虚拟卡生成", "手动输入"])
        self.card_mode_combo.currentTextChanged.connect(self.on_card_mode_changed)
        generator_layout.addWidget(self.card_mode_combo, 0, 1, 1, 3)

        # 第二行：BIN值 | 数量
        self.card_bin_label = QLabel("BIN值:")
        generator_layout.addWidget(self.card_bin_label, 1, 0)
        self.card_bin_input = QLineEdit()
        self.card_bin_input.setPlaceholderText("例如: 379240306")
        generator_layout.addWidget(self.card_bin_input, 1, 1)

        self.card_count_label = QLabel("数量:")
        generator_layout.addWidget(self.card_count_label, 1, 2)
        self.card_count_spin = QSpinBox()
        self.card_count_spin.setRange(1, 1000)
        self.card_count_spin.setValue(10)
        generator_layout.addWidget(self.card_count_spin, 1, 3)

        # 第三行：过期月份 | 过期年份
        self.card_month_label = QLabel("过期月份:")
        generator_layout.addWidget(self.card_month_label, 2, 0)
        self.card_month_combo = QComboBox()
        months = ["Random"] + [str(i).zfill(2) for i in range(1, 13)]
        self.card_month_combo.addItems(months)
        generator_layout.addWidget(self.card_month_combo, 2, 1)

        self.card_year_label = QLabel("过期年份:")
        generator_layout.addWidget(self.card_year_label, 2, 2)
        self.card_year_combo = QComboBox()
        years = ["Random"] + [str(i) for i in range(2025, 2036)]
        self.card_year_combo.addItems(years)
        generator_layout.addWidget(self.card_year_combo, 2, 3)

        # 第四行：CVV（跨两列）
        self.card_cvv_label = QLabel("CVV:")
        generator_layout.addWidget(self.card_cvv_label, 3, 0)
        self.card_cvv_input = QLineEdit()
        self.card_cvv_input.setPlaceholderText("留空则随机生成")
        generator_layout.addWidget(self.card_cvv_input, 3, 1, 1, 3)

        # 第五行：手动输入框（跨所有列）
        self.card_manual_label = QLabel("卡片列表:")
        self.card_manual_label.hide()
        generator_layout.addWidget(self.card_manual_label, 4, 0, Qt.AlignmentFlag.AlignTop)
        self.card_manual_text = QTextEdit()
        self.card_manual_text.setPlaceholderText(
            "格式：卡号|月份|年份|CVV\n"
            "每行一张卡，例如:\n"
            "379240306982617|03|2028|8844\n"
            "5123456789012346|12|2027|123"
        )
        self.card_manual_text.setMaximumHeight(70)
        self.card_manual_text.hide()
        generator_layout.addWidget(self.card_manual_text, 4, 1, 1, 3)

        # 第六行：按钮
        btn_layout = QHBoxLayout()
        self.card_generate_btn = QPushButton("🚀 生成卡片")
        self.card_generate_btn.clicked.connect(self.generate_cards)
        self.card_clear_btn = QPushButton("🗑️ 清空列表")
        self.card_clear_btn.clicked.connect(self.clear_cards)
        btn_layout.addWidget(self.card_generate_btn)
        btn_layout.addWidget(self.card_clear_btn)
        btn_layout.addStretch()
        generator_layout.addLayout(btn_layout, 5, 0, 1, 4)

        generator_group.setLayout(generator_layout)
        layout.addWidget(generator_group)

        # 底部：卡片列表
        list_group = QGroupBox("卡片列表")
        list_layout = QVBoxLayout()

        # 统计信息
        self.card_stats_label = QLabel("总数: 0 | 未使用: 0 | 已使用: 0")
        self.card_stats_label.setStyleSheet("color: #666; font-size: 12px;")
        list_layout.addWidget(self.card_stats_label)

        # 表格
        self.card_table = QTableWidget()
        self.card_table.setColumnCount(7)
        self.card_table.setHorizontalHeaderLabels(["ID", "卡号（脱敏）", "月份", "年份", "CVV", "类型", "状态"])
        self.card_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.card_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.card_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        list_layout.addWidget(self.card_table)

        # 操作按钮
        action_layout = QHBoxLayout()
        self.card_delete_btn = QPushButton("删除选中")
        self.card_delete_btn.clicked.connect(self.delete_selected_cards)
        self.card_refresh_btn = QPushButton("刷新")
        self.card_refresh_btn.clicked.connect(self.load_cards)
        action_layout.addWidget(self.card_delete_btn)
        action_layout.addWidget(self.card_refresh_btn)
        action_layout.addStretch()
        list_layout.addLayout(action_layout)

        list_group.setLayout(list_layout)
        layout.addWidget(list_group)

        widget.setLayout(layout)
        return widget

    def on_card_mode_changed(self, mode: str):
        """卡片生成模式改变"""
        if mode == "手动输入":
            self.card_bin_label.hide()
            self.card_bin_input.hide()
            self.card_month_label.hide()
            self.card_month_combo.hide()
            self.card_year_label.hide()
            self.card_year_combo.hide()
            self.card_cvv_label.hide()
            self.card_cvv_input.hide()
            self.card_count_label.hide()
            self.card_count_spin.hide()
            self.card_manual_label.show()
            self.card_manual_text.show()
        else:
            self.card_bin_label.show()
            self.card_bin_input.show()
            self.card_month_label.show()
            self.card_month_combo.show()
            self.card_year_label.show()
            self.card_year_combo.show()
            self.card_cvv_label.show()
            self.card_cvv_input.show()
            self.card_count_label.show()
            self.card_count_spin.show()
            self.card_manual_label.hide()
            self.card_manual_text.hide()

    def generate_cards(self):
        """生成卡片"""
        try:
            mode = self.card_mode_combo.currentText()

            if mode == "手动输入":
                # 解析手动输入
                card_string = self.card_manual_text.toPlainText()
                if not card_string.strip():
                    QMessageBox.warning(self, "警告", "请输入卡片信息！")
                    return

                cards = CardGenerator.parse_card_string(card_string)
            else:  # 虚拟卡生成
                bin_value = self.card_bin_input.text().strip()
                if not bin_value:
                    QMessageBox.warning(self, "警告", "请输入BIN值！")
                    return

                count = self.card_count_spin.value()
                month_option = self.card_month_combo.currentText().lower()
                year_option = self.card_year_combo.currentText().lower()
                cvv_option = self.card_cvv_input.text().strip() or "random"

                cards = CardGenerator.generate_cards(
                    bin_value=bin_value,
                    count=count,
                    month_option=month_option,
                    year_option=year_option,
                    cvv_option=cvv_option
                )

            # 保存到数据库
            count = self.db.add_cards_batch(cards)
            QMessageBox.information(self, "成功", f"成功生成 {count} 张卡片！")
            self.load_cards()

        except Exception as e:
            logger.error(f"生成卡片失败: {e}")
            QMessageBox.critical(self, "错误", f"生成卡片失败: {e}")

    def load_cards(self):
        """加载卡片列表"""
        try:
            cards = self.db.get_all_cards()
            self.card_table.setRowCount(len(cards))

            for row, card in enumerate(cards):
                self.card_table.setItem(row, 0, QTableWidgetItem(str(card.id)))
                self.card_table.setItem(row, 1, QTableWidgetItem(card.get_masked_number()))
                self.card_table.setItem(row, 2, QTableWidgetItem(card.month))
                self.card_table.setItem(row, 3, QTableWidgetItem(card.year))
                self.card_table.setItem(row, 4, QTableWidgetItem(card.cvc))
                self.card_table.setItem(row, 5, QTableWidgetItem(card.card_type))
                self.card_table.setItem(row, 6, QTableWidgetItem(card.status))

            # 更新统计
            total = len(cards)
            unused = self.db.get_card_count('unused')
            used = self.db.get_card_count('used')
            self.card_stats_label.setText(f"总数: {total} | 未使用: {unused} | 已使用: {used}")

        except Exception as e:
            logger.error(f"加载卡片失败: {e}")

    def delete_selected_cards(self):
        """删除选中的卡片"""
        selected_rows = self.card_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请先选择要删除的卡片！")
            return

        reply = QMessageBox.question(self, "确认", f"确定要删除选中的 {len(selected_rows)} 张卡片吗？")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                for row in selected_rows:
                    card_id = int(self.card_table.item(row.row(), 0).text())
                    self.db.delete_card(card_id)

                QMessageBox.information(self, "成功", "删除成功！")
                self.load_cards()
            except Exception as e:
                logger.error(f"删除卡片失败: {e}")
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def clear_cards(self):
        """清空卡片列表"""
        reply = QMessageBox.question(self, "确认", "确定要清空所有卡片吗？此操作不可恢复！")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                cards = self.db.get_all_cards()
                for card in cards:
                    self.db.delete_card(card.id)

                QMessageBox.information(self, "成功", "清空成功！")
                self.load_cards()
            except Exception as e:
                logger.error(f"清空卡片失败: {e}")
                QMessageBox.critical(self, "错误", f"清空失败: {e}")

    # ==================== 加载所有数据 ====================

    def load_all_data(self):
        """加载所有数据"""
        self.load_emails()
        self.load_users()
        self.load_cards()



