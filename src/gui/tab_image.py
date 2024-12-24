from PyQt6.QtWidgets import (QToolBar, QPushButton, QSpinBox,
                           QLabel, QRadioButton, QFileDialog,
                           QVBoxLayout, QHBoxLayout, QWidget,
                           QLineEdit, QMessageBox, QListWidget, QListWidgetItem, QTableWidgetItem, QTableWidget, QGroupBox, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QDateTime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from image_processor import ImageProcessor
from .base_tab import BaseTab

class ImageWorker(QObject):
    """图片处理工作线程"""
    finished = pyqtSignal()
    progress = pyqtSignal(int, int)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.image_processor = ImageProcessor()
        self.files = []
        self.input_root_dir = ""
        self.split_config = {}
        self.output_config = {}
        self.is_completed = False  # 添加完成标志
        
    def configure(self, files, input_root_dir, split_config, output_config):
        """配置处理参数"""
        self.files = files
        self.input_root_dir = input_root_dir
        self.split_config = split_config
        self.output_config = output_config
        self.is_completed = False  # 重置完成标志
        
    def process(self):
        """处理图片"""
        try:
            def progress_callback(current, total):
                self.progress.emit(current, total)
                
            def log_callback(msg):
                self.log.emit(msg)
                # 检查是否真正完成
                if msg == "处理完成":
                    self.is_completed = True
                    self.finished.emit()
                
            self.image_processor.split_images(
                files=self.files,
                input_root_dir=self.input_root_dir,
                split_config=self.split_config,
                output_config=self.output_config,
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            
        except Exception as e:
            self.error.emit(str(e))

class ImageTab(BaseTab):
    # 定义信号
    processing_started = pyqtSignal()
    processing_paused = pyqtSignal()
    processing_stopped = pyqtSignal()
    processing_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.is_paused = False
        self.file_paths = {}  # 初始化文件路径字典
        
        # 创建worker和线程
        self.worker = ImageWorker()
        self.thread = QThread()
        self.worker.moveToThread(self.thread)
        
        # 连接信号
        self.thread.started.connect(self.worker.process)
        self.worker.finished.connect(self.handle_finished)
        self.worker.progress.connect(self.update_progress)
        self.worker.error.connect(self.handle_error)
        self.worker.log.connect(self.log_message)
        
        # 连接控制按钮信号
        self.start_button.clicked.connect(self.start_processing)
        self.pause_button.clicked.connect(self.pause_processing)
        self.stop_button.clicked.connect(self.stop_processing)
        
        # 连接模式切换信号
        self.general_mode.toggled.connect(self.on_mode_changed)
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        
        # 添加文件按钮
        self.add_file_btn = QPushButton("添加文件")
        self.add_file_btn.clicked.connect(self.add_files)
        toolbar.addWidget(self.add_file_btn)
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        toolbar.addWidget(self.add_folder_btn)
        
        toolbar.addSeparator()
        
        # 清空列表按钮
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_files)
        toolbar.addWidget(self.clear_btn)
        
        # 删除选中按钮
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected)
        toolbar.addWidget(self.remove_btn)
        
        return toolbar
        
    def setup_settings_ui(self, layout):
        """设置右侧设置区域"""
        # 分割模式
        mode_group = QGroupBox("分割模式")
        mode_layout = QVBoxLayout()
        mode_layout.setSpacing(0)
        
        # 通用模式
        self.general_mode = QRadioButton("通用模式")
        self.general_mode.setChecked(True)
        general_desc = QLabel("    当图片较宽时左右切分，较高时上下切分")
        general_desc.setStyleSheet("color: #666666;")
        mode_layout.addWidget(self.general_mode)
        mode_layout.addWidget(general_desc)
        
        # 自定义模式
        self.custom_mode = QRadioButton("自定义模式")
        custom_desc = QLabel("    按指定尺寸横向切分，剩余部分纵向切分")
        custom_desc.setStyleSheet("color: #666666;")
        mode_layout.addWidget(self.custom_mode)
        mode_layout.addWidget(custom_desc)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # 目标尺寸
        size_group = QGroupBox("目标尺寸")
        size_layout = QVBoxLayout()
        
        # 宽度
        width_widget = QWidget()
        width_layout = QHBoxLayout()
        width_layout.setContentsMargins(0, 0, 0, 0)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(100, 10000)
        self.width_spin.setValue(800)
        self.width_spin.setSuffix(" px")
        self.width_spin.setEnabled(False)
        
        width_layout.addWidget(QLabel("宽度"))
        width_layout.addWidget(self.width_spin)
        width_layout.addStretch()
        
        width_widget.setLayout(width_layout)
        size_layout.addWidget(width_widget)
        
        # 高度
        height_widget = QWidget()
        height_layout = QHBoxLayout()
        height_layout.setContentsMargins(0, 0, 0, 0)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(100, 10000)
        self.height_spin.setValue(1200)
        self.height_spin.setSuffix(" px")
        self.height_spin.setEnabled(False)
        
        height_layout.addWidget(QLabel("高度"))
        height_layout.addWidget(self.height_spin)
        height_layout.addStretch()
        
        height_widget.setLayout(height_layout)
        size_layout.addWidget(height_widget)
        
        size_group.setLayout(size_layout)
        layout.addWidget(size_group)
        
        # 特殊处理选项
        special_group = QGroupBox("RAZ模式")
        special_layout = QVBoxLayout()
        
        special_desc = QLabel("    当图片较高时，将图片上下切分，并旋转底部部分")
        special_desc.setStyleSheet("color: #666666;")
        
        self.rotate_bottom_cb = QCheckBox("底部图片旋转180°")
        self.special_first_cb = QCheckBox("首页底部不旋转")
        
        special_layout.addWidget(special_desc)
        special_layout.addWidget(self.rotate_bottom_cb)
        special_layout.addWidget(self.special_first_cb)
        
        special_group.setLayout(special_layout)
        layout.addWidget(special_group)
        
        # 输出设置（使用基类的设置）
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        super().setup_settings_ui(output_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # 设置默认输出文件夹名
        self.output_name.setText("split_output")
        
        # 连接信号
        self.custom_mode.toggled.connect(self.on_mode_changed)
        
        layout.addStretch()
        
    def create_control_buttons(self):
        """创建控制按钮"""
        layout = QHBoxLayout()
        
        # 开始按钮
        self.start_button = QPushButton("开始处理")
        
        # 暂停按钮
        self.pause_button = QPushButton("暂停")
        self.pause_button.setEnabled(False)
        
        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        
        layout.addStretch()
        layout.addWidget(self.start_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.stop_button)
        layout.addStretch()
        
        # 连接信号
        self.start_button.clicked.connect(self.start_processing)
        self.pause_button.clicked.connect(self.pause_processing)
        self.stop_button.clicked.connect(self.stop_processing)
        
        return layout
        
    def on_mode_changed(self, checked):
        """分割模式改变时的处理"""
        self.width_spin.setEnabled(self.custom_mode.isChecked())
        self.height_spin.setEnabled(self.custom_mode.isChecked())
        
    def start_processing(self):
        """开始处理图片"""
        if self.file_list.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请添加需要处理的图片文件！")
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
            
        split_config = {
            'mode': 'custom' if self.custom_mode.isChecked() else 'general',
            'target_width': self.width_spin.value(),
            'target_height': self.height_spin.value(),
            'rotate_bottom': self.rotate_bottom_cb.isChecked(),
            'special_first': self.special_first_cb.isChecked()
        }
        
        # 获取输出配置
        output_config = self.get_output_config()
        
        try:
            # 配置worker
            self.worker.configure(
                files=files,
                input_root_dir=os.path.commonpath(files) if len(files) > 1 else os.path.dirname(files[0]),
                split_config=split_config,
                output_config=output_config
            )
            
            # 重置状态
            self.worker.image_processor.stop_event.clear()
            self.worker.image_processor.pause_event.set()
            
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
        
    def handle_finished(self):
        """处理完成"""
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
        
        # 只在真正完成时更新状态
        if self.worker.is_completed:
            self.is_processing = False
            self.update_control_buttons()
            QMessageBox.information(self, "完成", "图片处理已完成！")
        
    def pause_processing(self):
        """暂停处理"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.worker.image_processor.pause_event.clear()
            self.pause_button.setText("继续")
            self.processing_paused.emit()
        else:
            self.worker.image_processor.pause_event.set()
            self.pause_button.setText("暂停")
        self.update_control_buttons()
        
    def stop_processing(self):
        """停止处理"""
        if self.thread.isRunning():
            # 设置停止标志
            self.worker.image_processor.stop_event.set()
            
            # 如果当前是暂停状态，需要恢复以便能够退出
            if self.is_paused:
                self.worker.image_processor.pause_event.set()
            
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
        
    def update_control_buttons(self):
        """更新控制按钮状态"""
        self.start_button.setEnabled(not self.is_processing)
        self.pause_button.setEnabled(self.is_processing)
        self.stop_button.setEnabled(self.is_processing)
        
    def update_progress(self, current, total):
        """更新进度"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        
        # 只在真正完成时更新状态
        if current == total and self.worker.is_completed:
            self.is_processing = False
            self.update_control_buttons()
            self.processing_finished.emit()
            QMessageBox.information(self, "完成", "图片处理已完成！")

    def add_files(self):
        """添加文件"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片文件", "", "图片文件 (*.jpg *.png *.jpeg)")
        if files:
            for file_path in files:
                if file_path not in self.file_paths.values():
                    row = self.file_list.rowCount()
                    self.add_file_to_list(file_path)
                    self.file_paths[row] = file_path
                    
    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            for root, dirs, files in os.walk(folder):
                for file in files:
                    if file.lower().endswith(('.jpg', '.png', '.jpeg')):
                        file_path = os.path.join(root, file)
                        if file_path not in self.file_paths.values():
                            row = self.file_list.rowCount()
                            self.add_file_to_list(file_path)
                            self.file_paths[row] = file_path

    def clear_files(self):
        """清空文件列表"""
        self.file_list.setRowCount(0)
        self.file_paths.clear()
        
    def remove_selected(self):
        """删除选中文件"""
        selected_rows = sorted([item.row() for item in self.file_list.selectedItems()], reverse=True)
        for row in selected_rows:
            self.file_list.removeRow(row)
            if row in self.file_paths:
                del self.file_paths[row]
        
        # 重新整理file_paths的��引
        new_file_paths = {}
        for i in range(self.file_list.rowCount()):
            file_path = self.file_paths.get(i)
            if file_path:
                new_file_paths[i] = file_path
        self.file_paths = new_file_paths
        
    def log_message(self, message):
        """添加日志消息"""
        current_time = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.log_text.append(f"[{current_time}] {message}")
        
    def update_progress(self, current, total=100):
        """更新进度条"""
        self.progress_bar.setValue(current)
