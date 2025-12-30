# -*- coding: utf-8 -*-
"""
邮件监听功能Tab - 使用浏览器登录Outlook网页版
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QLabel, QLineEdit, QMessageBox, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont

from core.outlook.outlook_monitor import OutlookEmailMonitor
from core.outlook.outlook_api_monitor import OutlookAPIMonitor
from core.outlook.token_manager import TokenManager
from utils.logger import logger


class MonitorWorker(QThread):
    """邮件监听工作线程 - 支持浏览器和API两种模式"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    new_emails = pyqtSignal(list)  # 新邮件信号

    def __init__(self, email, password, interval=30, use_api=False):
        super().__init__()
        self.email = email
        self.password = password
        self.interval = interval
        self.is_running = True
        self.use_api = use_api  # 是否使用API模式
        self.monitor = None
        self.api_monitor = None
        self.token_manager = TokenManager()

        # 设置异常处理
        self.exception = None

    def run(self):
        """执行监听任务"""
        try:
            try:
                self.progress.emit("="*60)
                self.progress.emit(f"🚀 开始监听邮箱: {self.email}")
                self.progress.emit("="*60)

                # 检查是否有有效的token（用于API模式）
                token = None
                if self.use_api:
                    try:
                        token = self.token_manager.load_token(self.email)
                        if token:
                            self.progress.emit("✅ 找到有效的API token，使用API模式")
                            self._run_api_mode(token)
                            return
                        else:
                            self.progress.emit("⚠️  未找到有效的API token，切换到浏览器模式")
                            self.use_api = False
                    except Exception as e:
                        logger.error(f"加载token失败: {e}", exc_info=True)
                        self.progress.emit(f"⚠️  加载token失败，切换到浏览器模式: {str(e)}")
                        self.use_api = False

                # 浏览器模式
                self._run_browser_mode()

            except Exception as e:
                logger.error(f"监听失败: {e}", exc_info=True)
                self.progress.emit(f"❌ 监听失败: {str(e)}")
                self.finished.emit(False, f"监听失败: {str(e)}")
        except Exception as outer_e:
            # 最外层异常捕获，防止线程崩溃
            logger.error(f"监听线程崩溃: {outer_e}", exc_info=True)
            try:
                self.progress.emit(f"❌ 监听线程崩溃: {str(outer_e)}")
                self.finished.emit(False, f"监听线程崩溃: {str(outer_e)}")
            except:
                pass
        finally:
            # 关闭浏览器资源
            try:
                if self.monitor and hasattr(self.monitor, 'driver') and self.monitor.driver:
                    self.progress.emit("👋 正在关闭浏览器...")
                    try:
                        self.monitor.close()
                    except Exception as close_err:
                        logger.error(f"关闭浏览器异常: {close_err}")
                    self.progress.emit("✅ 浏览器已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}", exc_info=True)
                self.progress.emit(f"⚠️  关闭浏览器失败: {str(e)}")

    def _run_browser_mode(self):
        """浏览器模式 - 使用Selenium监听邮件"""
        import time

        try:
            # 创建监听器，传入进度回调
            self.monitor = OutlookEmailMonitor(
                self.email,
                self.password,
                progress_callback=lambda msg: self.progress.emit(msg)
            )

            # 启动浏览器
            self.progress.emit("🌐 正在启动浏览器...")
            try:
                if not self.monitor.start_browser():
                    self.progress.emit("❌ 浏览器启动失败，请检查Chrome是否已安装")
                    self.finished.emit(False, "浏览器启动失败")
                    return
            except Exception as e:
                logger.error(f"启动浏览器异常: {e}", exc_info=True)
                self.progress.emit(f"❌ 启动浏览器异常: {str(e)}")
                self.finished.emit(False, f"启动浏览器异常: {str(e)}")
                return

            # 登录
            self.progress.emit("🔐 正在登录Outlook...")
            try:
                if not self.monitor.login():
                    self.progress.emit("❌ 登录失败，请检查邮箱和密码")
                    self.finished.emit(False, "登录失败")
                    return
            except Exception as e:
                logger.error(f"登录异常: {e}", exc_info=True)
                self.progress.emit(f"❌ 登录异常: {str(e)}")
                self.finished.emit(False, f"登录异常: {str(e)}")
                return
        except Exception as e:
            logger.error(f"浏览器模式初始化失败: {e}", exc_info=True)
            self.progress.emit(f"❌ 初始化失败: {str(e)}")
            self.finished.emit(False, f"初始化失败: {str(e)}")
            return

        # 获取初始邮件列表
        try:
            self.progress.emit("📬 正在获取邮件列表...")
            emails = self.monitor.get_latest_emails(count=10)
            if emails:
                self.progress.emit(f"✅ 获取到 {len(emails)} 封邮件")
                formatted_emails = []
                for email_data in emails:
                    formatted_emails.append({
                        "from": email_data.get("sender", ""),
                        "subject": email_data.get("subject", ""),
                        "date": email_data.get("time", ""),
                        "body": email_data.get("body", "")
                    })
                self.new_emails.emit(formatted_emails)
            else:
                self.progress.emit("📭 收件箱为空")
        except Exception as e:
            logger.error(f"获取邮件列表失败: {e}", exc_info=True)
            self.progress.emit(f"⚠️  获取邮件列表失败: {str(e)}")
            emails = []

        # 开始持续监听
        self.progress.emit(f"\n⏰ 开始监听，每{self.interval}秒检查一次...")
        self.progress.emit("✅ 监听已启动，浏览器保持打开状态")

        last_email_count = len(emails) if emails else 0

        while self.is_running:
            try:
                time.sleep(self.interval)

                if not self.is_running:
                    break

                # 刷新页面获取最新邮件
                try:
                    self.progress.emit(f"\n🔄 [{time.strftime('%H:%M:%S')}] 检查新邮件...")
                    if self.monitor and self.monitor.driver:
                        self.monitor.driver.refresh()
                        time.sleep(3)
                    else:
                        self.progress.emit("⚠️  浏览器已关闭，停止监听")
                        break
                except Exception as e:
                    logger.error(f"刷新页面失败: {e}")
                    self.progress.emit(f"⚠️  刷新页面失败: {str(e)}")
                    continue

                # 获取最新邮件
                try:
                    new_emails = self.monitor.get_latest_emails(count=10)

                    if new_emails:
                        current_count = len(new_emails)

                        # 检测到新邮件
                        if current_count > last_email_count:
                            self.progress.emit(f"📨 检测到 {current_count - last_email_count} 封新邮件！")

                            # 只发送新邮件
                            new_email_list = new_emails[:current_count - last_email_count]
                            formatted_emails = []
                            for email_data in new_email_list:
                                formatted_emails.append({
                                    "from": email_data.get("sender", ""),
                                    "subject": email_data.get("subject", ""),
                                    "date": email_data.get("time", ""),
                                    "body": email_data.get("body", "")
                                })
                            self.new_emails.emit(formatted_emails)
                            last_email_count = current_count
                        else:
                            self.progress.emit("ℹ️  暂无新邮件")
                    else:
                        self.progress.emit("ℹ️  收件箱为空")
                except Exception as e:
                    logger.error(f"获取邮件失败: {e}", exc_info=True)
                    self.progress.emit(f"⚠️  获取邮件失败: {str(e)}")
                    continue

            except Exception as e:
                logger.error(f"监听循环异常: {e}", exc_info=True)
                self.progress.emit(f"⚠️  监听循环异常: {str(e)}")
                continue

        self.progress.emit("\n✅ 监听已停止")
        self.finished.emit(True, "监听已停止")

    def _run_api_mode(self, token):
        """API模式 - 使用Microsoft Graph API监听邮件"""
        import time

        try:
            # 创建API监听器
            self.api_monitor = OutlookAPIMonitor(
                self.email,
                token,
                progress_callback=lambda msg: self.progress.emit(msg)
            )

            # 测试连接
            if not self.api_monitor.test_connection():
                self.progress.emit("⚠️  API连接失败，token可能已过期")
                self.token_manager.delete_token(self.email)
                self.finished.emit(False, "API连接失败")
                return

            # 获取初始邮件列表
            self.progress.emit("📬 正在获取邮件列表...")
            emails = self.api_monitor.get_latest_emails(count=10)
        except Exception as e:
            logger.error(f"API模式初始化失败: {e}", exc_info=True)
            self.progress.emit(f"❌ API模式初始化失败: {str(e)}")
            self.finished.emit(False, f"API模式初始化失败: {str(e)}")
            return
        if emails:
            self.progress.emit(f"✅ 获取到 {len(emails)} 封邮件")
            formatted_emails = []
            for email_data in emails:
                formatted_emails.append({
                    "from": email_data.get("sender", ""),
                    "subject": email_data.get("subject", ""),
                    "date": email_data.get("time", ""),
                    "body": email_data.get("body", "")
                })
            self.new_emails.emit(formatted_emails)
        else:
            self.progress.emit("📭 收件箱为空")

        # 开始持续监听
        self.progress.emit(f"\n⏰ 开始监听，每{self.interval}秒检查一次...")
        self.progress.emit("✅ 监听已启动（API模式，浏览器已关闭）")

        last_email_count = len(emails) if emails else 0

        while self.is_running:
            try:
                time.sleep(self.interval)

                if not self.is_running:
                    break

                # 获取最新邮件
                self.progress.emit(f"\n🔄 [{time.strftime('%H:%M:%S')}] 检查新邮件...")
                new_emails = self.api_monitor.get_latest_emails(count=10)

                if new_emails:
                    current_count = len(new_emails)

                    # 检测到新邮件
                    if current_count > last_email_count:
                        self.progress.emit(f"📨 检测到 {current_count - last_email_count} 封新邮件！")

                        # 只发送新邮件
                        new_email_list = new_emails[:current_count - last_email_count]
                        formatted_emails = []
                        for email_data in new_email_list:
                            formatted_emails.append({
                                "from": email_data.get("sender", ""),
                                "subject": email_data.get("subject", ""),
                                "date": email_data.get("time", ""),
                                "body": email_data.get("body", "")
                            })
                        self.new_emails.emit(formatted_emails)
                        last_email_count = current_count
                    else:
                        self.progress.emit("ℹ️  暂无新邮件")
                else:
                    self.progress.emit("ℹ️  收件箱为空")

            except Exception as e:
                self.progress.emit(f"⚠️  检查邮件时出错: {str(e)}")
                logger.error(f"检查邮件失败: {e}")
                continue

        self.progress.emit("\n✅ 监听已停止")
        self.finished.emit(True, "监听已停止")

    def stop(self):
        """停止监听"""
        self.is_running = False
        # 关闭浏览器（如果使用浏览器模式）
        if self.monitor:
            try:
                self.monitor.close()
            except:
                pass
        # API模式不需要关闭任何资源，只需停止循环


class MonitorTab(QWidget):
    """邮件监听Tab"""
    
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # === 登录信息区域 - 紧凑布局 ===
        login_layout = QHBoxLayout()
        login_layout.setSpacing(10)
        login_layout.setContentsMargins(5, 5, 5, 5)
        
        # 邮箱输入
        login_layout.addWidget(QLabel("邮箱:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("your_email@outlook.com")
        self.email_input.setStyleSheet("padding: 5px; font-size: 12px;")
        login_layout.addWidget(self.email_input, 2)
        
        # 密码输入
        login_layout.addWidget(QLabel("密码:"))
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("密码")
        self.password_input.setStyleSheet("padding: 5px; font-size: 12px;")
        login_layout.addWidget(self.password_input, 2)
        
        # 检查间隔
        login_layout.addWidget(QLabel("间隔(秒):"))
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(10, 300)
        self.interval_spin.setValue(30)
        self.interval_spin.setStyleSheet("padding: 5px; font-size: 12px;")
        login_layout.addWidget(self.interval_spin)

        # API模式checkbox
        from PyQt6.QtWidgets import QCheckBox
        self.use_api_checkbox = QCheckBox("使用API模式")
        self.use_api_checkbox.setToolTip("如果有有效的token，使用API模式（更快）；否则使用浏览器模式")
        login_layout.addWidget(self.use_api_checkbox)
        
        # 开始按钮
        self.start_btn = QPushButton("📬 开始监听")
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
        self.start_btn.clicked.connect(self.start_monitor)
        login_layout.addWidget(self.start_btn)
        
        # 停止按钮
        self.stop_btn = QPushButton("⏹ 停止")
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
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_monitor)
        login_layout.addWidget(self.stop_btn)
        
        layout.addLayout(login_layout)
        
        # === 主体部分：上下分栏 ===
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === 上部：邮件列表 ===
        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_widget.setLayout(top_layout)
        
        top_layout.addWidget(QLabel("📬 收件箱"))
        
        # 邮件表格
        self.email_table = QTableWidget()
        self.email_table.setColumnCount(3)
        self.email_table.setHorizontalHeaderLabels(["发件人", "主题", "时间"])
        
        # 设置列宽
        header = self.email_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # 设置表格属性
        self.email_table.setAlternatingRowColors(True)
        self.email_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.email_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.email_table.itemSelectionChanged.connect(self.on_email_selected)
        
        top_layout.addWidget(self.email_table)
        
        splitter.addWidget(top_widget)
        
        # === 下部：邮件内容 ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)
        
        bottom_layout.addWidget(QLabel("📄 邮件内容"))
        
        self.email_content = QTextEdit()
        self.email_content.setReadOnly(True)
        self.email_content.setFont(QFont("Courier", 9))
        self.email_content.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd;")
        bottom_layout.addWidget(self.email_content)
        
        splitter.addWidget(bottom_widget)
        
        # 设置分栏比例
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # 存储邮件数据
        self.emails = []
    
    def fill_account_info(self, email, password):
        """填充账号信息"""
        self.email_input.setText(email)
        self.password_input.setText(password)
    
    def start_monitor(self):
        """开始监听"""
        try:
            email = self.email_input.text().strip()
            password = self.password_input.text().strip()

            if not email or not password:
                QMessageBox.warning(self, "警告", "请输入邮箱和密码！")
                return

            # 禁用开始按钮，启用停止按钮
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.email_input.setEnabled(False)
            self.password_input.setEnabled(False)
            self.interval_spin.setEnabled(False)
            self.use_api_checkbox.setEnabled(False)

            # 清空邮件列表
            self.email_table.setRowCount(0)
            self.email_content.clear()
            self.emails = []

            self.status_updated.emit("正在连接...")

            # 创建并启动工作线程
            try:
                interval = self.interval_spin.value()
                use_api = self.use_api_checkbox.isChecked()
                self.worker = MonitorWorker(email, password, interval, use_api=use_api)
                self.worker.progress.connect(self.append_log)
                self.worker.finished.connect(self.on_monitor_finished)
                self.worker.new_emails.connect(self.on_new_emails)
                self.worker.start()
            except Exception as e:
                logger.error(f"启动监听线程失败: {e}", exc_info=True)
                self.append_log(f"❌ 启动监听线程失败: {str(e)}")
                # 恢复UI状态
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.email_input.setEnabled(True)
                self.password_input.setEnabled(True)
                self.interval_spin.setEnabled(True)
                self.use_api_checkbox.setEnabled(True)
                QMessageBox.critical(self, "错误", f"启动监听失败: {str(e)}")
        except Exception as e:
            logger.error(f"start_monitor异常: {e}", exc_info=True)
            self.append_log(f"❌ 异常: {str(e)}")
            QMessageBox.critical(self, "错误", f"发生异常: {str(e)}")
    
    def stop_monitor(self):
        """停止监听"""
        if self.worker and self.worker.isRunning():
            self.append_log("⏹ 正在停止监听...")
            self.worker.stop()
            # 不要用wait()阻塞UI线程，改用finished信号来处理
            # worker会在finished信号中自动恢复UI状态
    
    def on_monitor_finished(self, success, message):
        """监听完成"""
        self.append_log(f"\n{message}")
        self.status_updated.emit(message)

        # 恢复按钮状态
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.email_input.setEnabled(True)
        self.password_input.setEnabled(True)
        self.interval_spin.setEnabled(True)
        self.use_api_checkbox.setEnabled(True)
    
    def on_new_emails(self, emails):
        """收到新邮件"""
        for email_data in emails:
            # 添加到列表开头
            self.emails.insert(0, email_data)
            
            # 添加到表格
            row = 0
            self.email_table.insertRow(row)
            self.email_table.setItem(row, 0, QTableWidgetItem(email_data.get("from", "")))
            self.email_table.setItem(row, 1, QTableWidgetItem(email_data.get("subject", "")))
            self.email_table.setItem(row, 2, QTableWidgetItem(email_data.get("date", "")))
    
    def on_email_selected(self):
        """选中邮件"""
        selected_rows = self.email_table.selectedIndexes()
        if not selected_rows:
            return
        
        row = selected_rows[0].row()
        if row < len(self.emails):
            email_data = self.emails[row]
            
            # 显示邮件内容
            content = f"发件人: {email_data.get('from', '')}\n"
            content += f"主题: {email_data.get('subject', '')}\n"
            content += f"时间: {email_data.get('date', '')}\n"
            content += "\n" + "="*60 + "\n\n"
            content += email_data.get('body', '')
            
            self.email_content.setPlainText(content)
    
    def append_log(self, message):
        """追加日志到邮件内容区域"""
        self.email_content.append(message)
        # 自动滚动到底部
        self.email_content.verticalScrollBar().setValue(
            self.email_content.verticalScrollBar().maximum()
        )

