# -*- coding: utf-8 -*-
"""
注册功能Tab
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

from core.outlook.outlook_register import OutlookRegistration
from utils.logger import get_logger
from utils.file_manager import FileManager
from utils.log_manager import LogManager
from config.settings import Settings

logger = get_logger(__name__)


class RegisterWorker(QThread):
    """注册工作线程 - 单次注册"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, dict)  # 成功/失败, 账号信息
    account_saved = pyqtSignal(dict)  # 账号保存信号
    need_confirm = pyqtSignal(str)  # 需要用户确认的信号
    request_close_browser = pyqtSignal()  # 请求关闭浏览器的信号
    need_confirm_success = pyqtSignal(str)  # 需要用户确认注册是否成功的信号

    def __init__(self):
        super().__init__()
        self.is_running = True
        self.registrar = None
        self.confirm_event = None
        self.log_lines = []  # 存储本次注册的日志行
        self.current_email = None  # 当前注册的邮箱
        self.close_browser_event = None  # 等待关闭浏览器的事件
        self.confirm_success_event = None  # 等待用户确认注册成功的事件
        self.confirm_success_result = False  # 用户确认的结果

    def wait_for_confirm(self, message):
        """等待用户确认（阻塞）"""
        from threading import Event
        self.confirm_event = Event()
        self.need_confirm.emit(message)
        self.confirm_event.wait()  # 阻塞等待确认

    def confirm_done(self):
        """用户确认完成"""
        if self.confirm_event:
            self.confirm_event.set()

    def wait_for_browser_close(self):
        """等待浏览器关闭确认（阻塞）"""
        from threading import Event
        self.close_browser_event = Event()
        self.request_close_browser.emit()
        self.close_browser_event.wait()  # 阻塞等待关闭确认

    def browser_close_done(self):
        """浏览器关闭完成"""
        if self.close_browser_event:
            self.close_browser_event.set()

    def wait_for_confirm_success(self, message):
        """等待用户确认注册是否成功（阻塞），返回True/False"""
        from threading import Event
        self.confirm_success_event = Event()
        self.confirm_success_result = False  # 默认失败
        self.need_confirm_success.emit(message)
        self.confirm_success_event.wait()  # 阻塞等待确认
        return self.confirm_success_result

    def confirm_success_done(self, success):
        """用户确认注册成功/失败"""
        self.confirm_success_result = success
        if self.confirm_success_event:
            self.confirm_success_event.set()

    def run(self):
        """执行单次注册任务"""
        try:
            self.progress.emit("="*60)
            self.progress.emit("🚀 开始新的注册任务")
            self.progress.emit("="*60)

            # 创建注册器
            self.registrar = OutlookRegistration(
                progress_callback=lambda msg: self.progress.emit(msg),
                confirm_callback=self.wait_for_confirm,
                confirm_success_callback=self.wait_for_confirm_success  # 🔥 添加成功确认回调
            )

            # 执行注册
            result = self.registrar.register()

            # 获取账号信息
            user_info = self.registrar.user_info if hasattr(self.registrar, 'user_info') else {}

            if result:
                self.progress.emit("\n✅ 注册流程完成！")
                self.finished.emit(True, user_info)
            else:
                self.progress.emit("\n❌ 注册失败")
                self.finished.emit(False, user_info)

            # 🔥 关键修改：等待用户在UI确认后再关闭浏览器
            self.progress.emit("\n⏳ 等待用户确认后关闭浏览器...")
            self.wait_for_browser_close()

            # 关闭浏览器
            self.progress.emit("👋 正在关闭浏览器...")
            self.registrar.close()
            self.progress.emit("✅ 浏览器已关闭")

        except Exception as e:
            logger.error(f"注册异常: {e}")
            self.progress.emit(f"\n❌ 注册异常: {str(e)}")
            self.finished.emit(False, {})

            # 异常时也要关闭浏览器
            try:
                if self.registrar:
                    self.registrar.close()
            except:
                pass

    def stop(self):
        """停止任务"""
        self.is_running = False
        if self.registrar:
            try:
                self.registrar.close()
            except:
                pass


class RegisterTab(QWidget):
    """注册功能Tab"""
    status_updated = pyqtSignal(str)
    switch_to_monitor = pyqtSignal(str, str)  # 切换到监听Tab的信号(email, password)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.accounts = []
        self.current_log_email = None  # 当前查看日志的邮箱
        self.account_logs = {}  # 存储每个账号的注册日志 {email: [log_lines]}
        self.current_registering_email = None  # 当前正在注册的邮箱
        self.init_ui()
        self.load_accounts()

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === 控制面板 - 紧凑布局 ===
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        control_layout.setContentsMargins(5, 5, 5, 5)

        control_layout.addStretch()

        # 按钮 - 缩小尺寸
        self.start_btn = QPushButton("🚀 开始注册")
        self.start_btn.clicked.connect(self.start_register)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-size: 13px;
                padding: 6px 20px;
                border-radius: 4px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.clicked.connect(self.stop_register)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 13px;
                padding: 6px 20px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        control_layout.addWidget(self.start_btn)
        control_layout.addWidget(self.stop_btn)

        layout.addLayout(control_layout)

        # === 主体部分：左右分栏 ===
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # === 左侧：账号列表 ===
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        left_layout.addWidget(QLabel("📋 已注册账号列表"))

        # 账号表格
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(5)
        self.account_table.setHorizontalHeaderLabels(["邮箱", "密码", "注册时间", "状态", "操作"])

        # 设置列宽
        header = self.account_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.account_table.setColumnWidth(4, 80)  # 操作列宽度（只有监听和删除两个按钮）

        # 设置表格属性
        self.account_table.setAlternatingRowColors(True)
        self.account_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.account_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # 连接表格点击事件 - 点击行时显示日志
        self.account_table.itemSelectionChanged.connect(self.on_account_row_selected)

        left_layout.addWidget(self.account_table)

        # 刷新按钮 - 紧凑样式
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                font-size: 12px;
                border-radius: 3px;
                background-color: #607D8B;
                color: white;
            }
            QPushButton:hover {
                background-color: #455A64;
            }
        """)
        refresh_btn.clicked.connect(self.load_accounts)
        left_layout.addWidget(refresh_btn)

        splitter.addWidget(left_widget)

        # === 右侧：日志输出 ===
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        self.log_title = QLabel("📝 注册日志")
        self.log_title.setStyleSheet("font-size: 13px; font-weight: bold; padding: 2px;")
        right_layout.addWidget(self.log_title)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        self.log_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        right_layout.addWidget(self.log_text)

        # 清空日志按钮 - 紧凑样式
        clear_btn = QPushButton("🗑️ 清空日志")
        clear_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                font-size: 12px;
                border-radius: 3px;
                background-color: #9E9E9E;
                color: white;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        clear_btn.clicked.connect(self.log_text.clear)
        right_layout.addWidget(clear_btn)

        splitter.addWidget(right_widget)

        # 设置分栏比例 (左:右 = 3:2)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter)
    
    def load_accounts(self):
        """加载账号列表"""
        logger.info("加载账号列表")
        self.accounts = FileManager.load_accounts()
        self.update_account_table()
        self.status_updated.emit(f"已加载 {len(self.accounts)} 个账号")

    def update_account_table(self):
        """更新账号表格"""
        self.account_table.setRowCount(len(self.accounts))

        for i, account in enumerate(self.accounts):
            # 邮箱
            self.account_table.setItem(i, 0, QTableWidgetItem(account.get('email', '')))

            # 密码
            self.account_table.setItem(i, 1, QTableWidgetItem(account.get('password', '')))

            # 注册时间
            self.account_table.setItem(i, 2, QTableWidgetItem(account.get('created_at', '')))

            # 状态
            status = account.get('status', '未知')
            status_item = QTableWidgetItem(status)
            if status == '已注册':
                status_item.setBackground(QColor(76, 175, 80, 50))  # 绿色
            else:
                status_item.setBackground(QColor(255, 152, 0, 50))  # 橙色
            self.account_table.setItem(i, 3, status_item)

            # 操作按钮容器
            btn_widget = QWidget()
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(4, 2, 4, 2)
            btn_layout.setSpacing(4)
            btn_widget.setLayout(btn_layout)

            # 监听按钮 - 缩小尺寸
            monitor_btn = QPushButton("📬")
            monitor_btn.setToolTip("监听邮件")
            monitor_btn.setStyleSheet("""
                QPushButton {
                    padding: 3px 8px;
                    font-size: 12px;
                    border-radius: 3px;
                    background-color: #2196F3;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            monitor_btn.clicked.connect(lambda checked, acc=account: self.on_monitor_clicked(acc))
            btn_layout.addWidget(monitor_btn)

            # 删除按钮 - 缩小尺寸
            delete_btn = QPushButton("🗑️")
            delete_btn.setToolTip("删除账号")
            delete_btn.setStyleSheet("""
                QPushButton {
                    padding: 3px 8px;
                    font-size: 12px;
                    border-radius: 3px;
                    background-color: #f44336;
                    color: white;
                }
                QPushButton:hover {
                    background-color: #d32f2f;
                }
            """)
            delete_btn.clicked.connect(lambda checked, acc=account: self.on_delete_clicked(acc))
            btn_layout.addWidget(delete_btn)

            self.account_table.setCellWidget(i, 4, btn_widget)

    def on_account_row_selected(self):
        """表格行被选中时 - 显示该账号的日志"""
        selected_rows = self.account_table.selectedIndexes()
        if not selected_rows:
            return

        # 获取选中行的账号
        row = selected_rows[0].row()
        if row < len(self.accounts):
            account = self.accounts[row]
            self.on_log_clicked(account)

    def on_monitor_clicked(self, account):
        """点击监听按钮"""
        email = account.get('email', '')
        password = account.get('password', '')
        self.switch_to_monitor.emit(email, password)

    def on_log_clicked(self, account):
        """点击日志按钮 - 显示该账号的注册日志"""
        email = account.get('email', '')
        self.current_log_email = email
        self.log_title.setText(f"📝 注册日志 - {email}")

        # 清空日志区域
        self.log_text.clear()

        # 显示账号基本信息
        self.log_text.append("="*60)
        self.log_text.append(f"📬 账号信息")
        self.log_text.append("="*60)
        self.log_text.append(f"邮箱: {email}")
        self.log_text.append(f"密码: {account.get('password', '')}")
        self.log_text.append(f"生日: {account.get('birthday', '')}")
        self.log_text.append(f"状态: {account.get('status', '')}")
        self.log_text.append(f"创建时间: {account.get('created_at', '')}")
        self.log_text.append("")

        # 显示注册日志 - 优先从文件加载
        log_lines = LogManager.load_log(email)

        if log_lines:
            self.log_text.append("="*60)
            self.log_text.append(f"📝 注册过程日志")
            self.log_text.append("="*60)
            for log_line in log_lines:
                self.log_text.append(log_line)
        else:
            self.log_text.append("="*60)
            self.log_text.append("⚠️ 暂无注册日志")
            self.log_text.append("="*60)
            self.log_text.append("该账号可能是在本次启动前注册的，")
            self.log_text.append("或者注册过程中未记录日志。")

    def on_delete_clicked(self, account):
        """点击删除按钮"""
        email = account.get('email', '')

        # 二次确认
        reply = QMessageBox.question(
            self,
            '确认删除',
            f'确定要删除账号吗？\n\n邮箱: {email}\n\n此操作不可恢复！',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从文件中删除
                accounts = FileManager.load_accounts()
                accounts = [acc for acc in accounts if acc.get('email') != email]

                # 重新写入文件（使用正确的格式）
                with open(Settings.ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
                    for acc in accounts:
                        f.write(f"状态: {acc.get('status', '未知')}\n")
                        f.write(f"邮箱: {acc.get('email', '')}\n")
                        f.write(f"密码: {acc.get('password', '')}\n")
                        f.write(f"生日: {acc.get('birthday', '')}\n")
                        f.write(f"创建时间: {acc.get('created_at', '')}\n")
                        f.write("-" * 50 + "\n")

                # 同时删除对应的日志文件
                LogManager.delete_log(email)

                QMessageBox.information(self, "成功", f"账号已删除: {email}")
                self.load_accounts()
                logger.info(f"删除账号: {email}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败:\n{str(e)}")
                logger.error(f"删除账号失败: {e}")

    def start_register(self):
        """开始注册"""
        # 确认对话框
        # reply = QMessageBox.question(
        #     self,
        #     '确认注册',
        #     '确定要开始注册新的Outlook账号吗？\n\n注意：\n1. 注册过程中可能需要手动完成验证码\n2. 此操作仅用于测试目的！',
        #     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        #     QMessageBox.StandardButton.No
        # )

        # if reply != QMessageBox.StandardButton.Yes:
        #     return

        # 禁用开始按钮，启用停止按钮
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 清空日志
        self.log_text.clear()
        self.log_title.setText("📝 注册日志 - 实时")
        self.current_log_email = None
        self.append_log("开始注册任务...")
        self.status_updated.emit("正在注册...")

        # 创建并启动工作线程
        self.worker = RegisterWorker()
        self.worker.progress.connect(self.append_log)
        self.worker.finished.connect(self.on_register_finished)
        self.worker.need_confirm.connect(self.on_need_confirm)
        self.worker.need_confirm_success.connect(self.on_need_confirm_success)  # 🔥 连接成功确认信号
        self.worker.start()
    
    def stop_register(self):
        """停止注册"""
        if self.worker and self.worker.isRunning():
            self.append_log("\n⏹ 正在停止注册任务...")
            self.worker.stop()
            self.worker.wait()

    def on_need_confirm(self, message):
        """需要用户确认（验证码完成等）"""
        # 弹出对话框
        QMessageBox.information(
            self,
            '需要手动操作',
            f'{message}\n\n请在浏览器中完成操作后，点击"确定"继续。',
            QMessageBox.StandardButton.Ok
        )

        # 通知worker继续
        if self.worker:
            self.worker.confirm_done()

    def on_need_confirm_success(self, message):
        """需要用户确认注册是否成功"""
        # 🔥 弹出Yes/No对话框，让用户选择注册是否成功
        reply = QMessageBox.question(
            self,
            '确认注册结果',
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes  # 默认选择"是"
        )

        # 根据用户选择通知worker
        success = (reply == QMessageBox.StandardButton.Yes)
        if self.worker:
            self.worker.confirm_success_done(success)

    def on_register_finished(self, success, user_info):
        """注册完成（用户已经在注册流程中确认过成功/失败了）"""
        if success:
            self.append_log("\n✅ 注册成功！")
            self.status_updated.emit("注册成功")

            # 刷新账号列表
            self.load_accounts()

            # 注册完成后，清空当前注册邮箱标记（准备下一次注册）
            self.current_registering_email = None

            # 🔥 显示简单的完成提示
            QMessageBox.information(
                self,
                "注册成功",
                f"✅ 注册成功！\n\n邮箱: {user_info.get('email', 'N/A')}\n密码: {user_info.get('password', 'N/A')}\n\n点击【确定】后将关闭浏览器。"
            )
        else:
            self.append_log("\n❌ 注册失败")
            self.status_updated.emit("注册失败")

            # 失败时也清空当前注册邮箱标记
            self.current_registering_email = None

            # 显示失败提示
            QMessageBox.warning(
                self,
                "注册失败",
                f"❌ 注册失败\n\n邮箱: {user_info.get('email', 'N/A')}\n\n请查看日志了解详情。\n\n点击【确定】后将关闭浏览器。"
            )

        # 🔥 用户点击确定后，通知worker关闭浏览器
        if self.worker:
            self.worker.browser_close_done()

        # 恢复按钮状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def append_log(self, message):
        """追加日志"""
        # 显示到UI
        self.log_text.append(message)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

        # 如果正在注册，保存到对应账号的日志
        if self.current_registering_email:
            if self.current_registering_email not in self.account_logs:
                self.account_logs[self.current_registering_email] = []
            self.account_logs[self.current_registering_email].append(message)

            # 同时保存到文件
            LogManager.append_log(self.current_registering_email, message)

        # 检测邮箱生成的日志，提取邮箱地址
        if "生成邮箱:" in message or "📧 生成邮箱:" in message:
            # 提取邮箱地址
            parts = message.split(":")
            if len(parts) >= 2:
                email = parts[1].strip()
                self.current_registering_email = email
                # 初始化该邮箱的日志列表
                self.account_logs[email] = [message]

