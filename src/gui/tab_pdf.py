from PyQt6.QtWidgets import (QToolBar, QPushButton, QSpinBox,
                                 QComboBox, QLabel, QRadioButton, QFileDialog,
                                 QVBoxLayout, QHBoxLayout, QWidget, QLineEdit, QMessageBox, QGroupBox,
                                 QTableWidgetItem, QScrollBar)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QDateTime
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pdf_processor import PDFProcessor
from .base_tab import BaseTab

class PDFWorker(QObject):
    """PDF处理工作线程"""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.pdf_processor = PDFProcessor()
        self.files = []
        self.dpi = 150
        self.output_format = 'PNG'
        self.interval = 0
        self.output_location = "原位置"
        self.custom_output_path = None
        self.split_config = None
        
    def configure(self, files, dpi, output_format, interval, 
                 output_location, custom_output_path, split_config=None):
        """配置处理参数"""
        self.files = files
        self.dpi = dpi
        self.output_format = output_format
        self.interval = interval
        self.output_location = output_location
        self.custom_output_path = custom_output_path
        self.split_config = split_config
        
    def process(self):
        """处理PDF文件"""
        try:
            def progress_callback(value):
                self.progress.emit(value)
                
            def log_callback(msg):
                self.log.emit(msg)
                
            self.pdf_processor.process_files(
                files=self.files,
                dpi=self.dpi,
                output_format=self.output_format,
                interval=self.interval,
                output_location=self.output_location,
                custom_output_path=self.custom_output_path,
                split_config=self.split_config,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))

class PDFTab(BaseTab):
    # 定义信号
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_paused = pyqtSignal()
    processing_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.is_paused = False
        self.worker = PDFWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        self.setup_worker_connections()
        self.setup_ui_connections()
        
    def setup_worker_connections(self):
        """设置工作线程的信号连接"""
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self.handle_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.handle_error)
        self.worker.log.connect(self.log_message)
        
    def setup_ui_connections(self):
        """设置UI控件的信号连接"""
        # 工具栏按钮连接
        self.add_file_btn.clicked.connect(self.add_files)
        self.add_folder_btn.clicked.connect(self.add_folder)
        self.clear_btn.clicked.connect(self.clear_list)
        self.remove_btn.clicked.connect(self.remove_selected)
        
        # 控制按钮连接
        self.start_button.clicked.connect(self.start_processing)
        self.pause_button.clicked.connect(self.pause_processing)
        self.stop_button.clicked.connect(self.stop_processing)
        
    def create_toolbar(self):
        """创建PDF标签页的工具栏"""
        toolbar = QToolBar()
        
        # 添加文件按钮
        self.add_file_btn = QPushButton("添加文件")
        toolbar.addWidget(self.add_file_btn)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加文件夹")
        toolbar.addWidget(self.add_folder_btn)
        
        toolbar.addSeparator()
        
        # 清空列表按钮
        self.clear_btn = QPushButton("清空列表")
        toolbar.addWidget(self.clear_btn)
        
        # 删除选中按钮
        self.remove_btn = QPushButton("删除选中")
        toolbar.addWidget(self.remove_btn)
        
        return toolbar
        
    def setup_settings_ui(self, layout):
            """设置PDF转换的设置界面"""
            # 设置区域
            settings_widget = QWidget()
            settings_layout = QVBoxLayout()
            
            # 转换设置组
            convert_group = QGroupBox("转换设置")
            convert_layout = QVBoxLayout()
            
            # DPI设置
            dpi_widget = QWidget()
            dpi_layout = QHBoxLayout()
            dpi_layout.setContentsMargins(0, 0, 0, 0)
            
            self.dpi_combo = QComboBox()
            dpi_values = ["150", "300", "600"]
            self.dpi_combo.addItems(dpi_values)
            self.dpi_combo.setCurrentText("150")  # 设置默认值为150
            
            dpi_layout.addWidget(QLabel("分辨率"))
            dpi_layout.addWidget(self.dpi_combo)
            dpi_layout.addWidget(QLabel("DPI"))
            dpi_layout.addStretch()
            
            dpi_widget.setLayout(dpi_layout)
            convert_layout.addWidget(dpi_widget)

            # 间隔设置
            interval_widget = QWidget()
            interval_layout = QHBoxLayout()
            interval_layout.setContentsMargins(0, 0, 0, 0)
            
            self.interval_combo = QComboBox()
            interval_values = ["0 (处理所有页面)"] + [str(i) for i in range(1, 11)]
            self.interval_combo.addItems(interval_values)
            
            interval_layout.addWidget(QLabel("处理间隔"))
            interval_layout.addWidget(self.interval_combo)
            interval_layout.addStretch()
            
            interval_widget.setLayout(interval_layout)
            convert_layout.addWidget(interval_widget)
            
            convert_group.setLayout(convert_layout)
            settings_layout.addWidget(convert_group)
            
            # 输出设置（使用基类的设置）
            output_group = QGroupBox("输出设置")
            output_layout = QVBoxLayout()
            super().setup_settings_ui(output_layout)
            output_group.setLayout(output_layout)
            settings_layout.addWidget(output_group)
            
            # 设置默认输出文件夹名
            self.output_name.setText("pdf_output")
            
            settings_layout.addStretch()
            settings_widget.setLayout(settings_layout)
            layout.addWidget(settings_widget)
        
    def create_control_buttons(self):
        """创建控制按钮"""
        control_layout = QHBoxLayout()
        
        # 开始按钮
        self.start_button = QPushButton("开始处理")
        self.start_button.clicked.connect(self.start_processing)
        
        # 暂停按钮
        self.pause_button = QPushButton("暂停")
        self.pause_button.clicked.connect(self.pause_processing)
        self.pause_button.setEnabled(False)
        
        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_processing)
        self.stop_button.setEnabled(False)
        
        control_layout.addStretch()
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.pause_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        
        return control_layout
        
    def add_files(self):
        """添加PDF文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择PDF文件",
            "",
            "PDF文件 (*.pdf)"
        )
        if files:
            for file_path in files:
                if os.path.exists(file_path):
                    self.add_file_to_list(file_path)
                    self.file_paths[self.file_list.rowCount() - 1] = file_path
                    
    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "选择包含PDF文件的文件夹"
        )
        if folder:
            for root, _, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith('.pdf'):
                        file_path = os.path.join(root, file)
                        self.add_file_to_list(file_path)
                        self.file_paths[self.file_list.rowCount() - 1] = file_path
                        
    def clear_list(self):
        """清空文件列表"""
        self.file_list.setRowCount(0)
        self.file_paths.clear()
        
    def remove_selected(self):
        """删除选中的文件"""
        rows = sorted([item.row() for item in self.file_list.selectedItems()])
        for row in reversed(rows):
            self.file_list.removeRow(row)
            if row in self.file_paths:
                del self.file_paths[row]
                
    def start_processing(self):
        """开始处理"""
        if self.file_list.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先添加需要处理的PDF文件！")
            return
            
        if self.output_custom.isChecked() and not self.output_path.text():
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
            
        self.is_processing = True
        self.is_paused = False
        self.update_control_buttons()
        
        # 收集处理参数
        files = []
        for i in range(self.file_list.rowCount()):
            files.append(self.file_paths[i])
            
        try:
            # 构建split_config
            split_config = {
                'output_name': self.output_name.text() or "pdf_output"  # 使用输出名称或默认值
            }
            
            # 配置worker
            self.worker.configure(
                files=files,
                dpi=int(self.dpi_combo.currentText()),
                output_format='PNG',
                interval=int(self.interval_combo.currentText().split(' ')[0]),
                output_location="原位置" if self.output_original.isChecked() else "自定义位置",
                custom_output_path=self.output_path.text() if self.output_custom.isChecked() else None,
                split_config=split_config  # 添加split_config参数
            )
            
            # 重置状态
            self.worker.pdf_processor.stop_event.clear()
            self.worker.pdf_processor.pause_event.set()
            
            # 开始处理
            self.thread.start()
            self.processing_started.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"处理过程中出错：{str(e)}")
            self.is_processing = False
            self.update_control_buttons()
    
    def handle_error(self, error_msg):
        """处理错误"""
        self.log_message(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", f"处理过程中出错：{error_msg}")
        self.is_processing = False
        self.update_control_buttons()
        
    def pause_processing(self):
        """暂停处理"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.worker.pdf_processor.pause_event.clear()
            self.pause_button.setText("继续")
            self.processing_paused.emit()
        else:
            self.worker.pdf_processor.pause_event.set()
            self.pause_button.setText("暂停")
        self.update_control_buttons()
        
    def stop_processing(self):
        """停止处理"""
        if self.thread.isRunning():
            # 设置停止标志
            self.worker.pdf_processor.stop_event.set()
            
            # 如果当前是暂停状态，需要恢复以便能够退出
            if self.is_paused:
                self.worker.pdf_processor.pause_event.set()
            
            # 等待线程完成
            self.thread.quit()
            self.thread.wait()
            
            # 重置状态
            self.is_processing = False
            self.is_paused = False
            
            # 重置进度条
            self.progress_bar.setValue(0)
            
            # 更新UI状态
            self.processing_stopped.emit()
            self.update_control_buttons()
            
            # 更新所有文件状态
            for row in range(self.file_list.rowCount()):
                self.update_file_status(row, "已停止")
            
            # 添加日志
            self.log_message("处理已停止")
        
    def disable_settings(self):
        """禁用设置和文件操作"""
        self.dpi_combo.setEnabled(False)
        self.interval_combo.setEnabled(False)
        self.original_radio.setEnabled(False)
        self.custom_radio.setEnabled(False)
        self.custom_path.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.add_file_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        
    def enable_settings(self):
        """启用设置和文件操作"""
        self.dpi_combo.setEnabled(True)
        self.interval_combo.setEnabled(True)
        self.original_radio.setEnabled(True)
        self.custom_radio.setEnabled(True)
        self.custom_path.setEnabled(self.custom_radio.isChecked())
        self.browse_btn.setEnabled(self.custom_radio.isChecked())
        self.add_file_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)

    def get_output_path(self, input_path):
        """获取输出路径"""
        if self.original_radio.isChecked():
            return os.path.dirname(input_path)
        return self.custom_path.text()
        
    def get_settings(self):
        """获取当前设置"""
        return {
            'dpi': int(self.dpi_combo.currentText()),
            'interval': int(self.interval_combo.currentText().split(' ')[0]),
            'use_original_location': self.original_radio.isChecked(),
            'output_path': self.custom_path.text() if self.custom_radio.isChecked() else None
        }

    def update_control_buttons(self):
        """更新控制按钮状态"""
        self.start_button.setEnabled(not self.is_processing)
        self.pause_button.setEnabled(self.is_processing)
        self.stop_button.setEnabled(self.is_processing)
        
        # 更新暂停按钮文本
        self.pause_button.setText("继续" if self.is_paused else "暂停")
        
        # 处理时禁用文件操作和设置
        self.add_file_btn.setEnabled(not self.is_processing)
        self.add_folder_btn.setEnabled(not self.is_processing)
        self.clear_btn.setEnabled(not self.is_processing)
        self.remove_btn.setEnabled(not self.is_processing)
        self.dpi_combo.setEnabled(not self.is_processing)
        self.interval_combo.setEnabled(not self.is_processing)

    def update_progress(self, value):
        """更新进度"""
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
            # 只在进度达到100%时更新文件状态
            if value >= 100:
                for row in range(self.file_list.rowCount()):
                    self.update_file_status(row, "处理完成")
                # 不在这里调用handle_finished，让worker的finished信号来触发它
    
    def handle_finished(self):
        """处理完成"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        
        self.is_processing = False
        self.update_control_buttons()
        self.processing_finished.emit()
        self.log_message("处理完成")
        
        # 只在真正完成时显示消息框
        if not self.worker.pdf_processor.stop_event.is_set():
            QMessageBox.information(self, "完成", "PDF处理已完成！")

    def add_file_to_list(self, file_path):
        """添加文件到列表"""
        try:
            file_info = os.stat(file_path)
            row = self.file_list.rowCount()
            self.file_list.insertRow(row)
            
            # 文件名
            file_name = os.path.basename(file_path)
            self.file_list.setItem(row, 0, QTableWidgetItem(file_name))
            
            # 文件大小
            size = self.format_size(file_info.st_size)
            self.file_list.setItem(row, 1, QTableWidgetItem(size))
            
            # 修改时间
            mtime = QDateTime.fromSecsSinceEpoch(int(file_info.st_mtime))
            self.file_list.setItem(row, 2, QTableWidgetItem(mtime.toString("yyyy-MM-dd HH:mm:ss")))
            
            # 状态
            self.file_list.setItem(row, 3, QTableWidgetItem("等待处理"))
            
            # 存储文件路径
            self.file_paths[row] = file_path
            
        except Exception as e:
            self.log_message(f"添加文件失败: {str(e)}")
            
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def update_file_status(self, row, status):
        """更新文件状态"""
        if 0 <= row < self.file_list.rowCount():
            self.file_list.setItem(row, 3, QTableWidgetItem(status))
            
    def log_message(self, message):
        """添加日志消息"""
        if hasattr(self, 'log_text'):
            current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
            self.log_text.append(f"[{current_time}] {message}")
            # 滚动到底部
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """拖拽放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                self.add_file_to_list(file_path)
            elif os.path.isdir(file_path):
                for root, _, files in os.walk(file_path):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            pdf_path = os.path.join(root, file)
                            self.add_file_to_list(pdf_path)
                            
    def cleanup(self):
        """清理资源"""
        if self.thread.isRunning():
            self.worker.pdf_processor.stop_event.set()
            self.thread.quit()
            self.thread.wait()
        self.worker.deleteLater()
        self.thread.deleteLater()
        
    def closeEvent(self, event):
        """关闭事件"""
        if self.is_processing:
            reply = QMessageBox.question(
                self,
                "确认",
                "正在处理文件，确定要关闭吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
                
        self.cleanup()
        super().closeEvent(event)
