from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                                 QTableWidget, QGroupBox, QPushButton, 
                                 QProgressBar, QTextEdit, QSplitter,
                                 QTableWidgetItem, QHeaderView, QFileDialog,
                                 QMessageBox, QToolBar, QStyle, QRadioButton, QLineEdit, QLabel)
from PyQt6.QtCore import Qt, QSize, QDateTime, QMimeData
from PyQt6.QtGui import QIcon, QDragEnterEvent, QDropEvent
import os

class BaseTab(QWidget):
    def __init__(self):
        super().__init__()
        self.file_paths = {}  # 存储文件完整路径
        self.init_ui()
        
    def init_ui(self):
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建上部分的分割器
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧部分（文件列表和工具栏）
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 添加工具栏（PDF和图片标签页会重写这个方法）
        self.toolbar = self.create_toolbar()
        if self.toolbar:
            left_layout.addWidget(self.toolbar)
        
        # 文件列表
        self.file_list = QTableWidget()
        self.setup_file_list()
        left_layout.addWidget(self.file_list)
        
        top_splitter.addWidget(left_widget)
        
        # 右侧设置区域
        settings_group = QGroupBox("设置")
        settings_layout = QVBoxLayout(settings_group)
        self.setup_settings_ui(settings_layout)  # 子类将实现此方法
        top_splitter.addWidget(settings_group)
        
        # 设置分割比例
        top_splitter.setStretchFactor(0, 7)  # 文件列表占70%
        top_splitter.setStretchFactor(1, 3)  # 设置区域占30%
        
        # 下部分控制区域
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # 控制按钮布局
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("开始处理")
        self.pause_button = QPushButton("暂停")
        self.stop_button = QPushButton("停止")
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addStretch()
        
        # 进度条
        self.progress_bar = QProgressBar()
        
        # 日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        
        # 添加到下部分布局
        bottom_layout.addLayout(button_layout)
        bottom_layout.addWidget(self.progress_bar)
        bottom_layout.addWidget(self.log_text)
        
        # 设置上下部分的比例
        main_layout.addWidget(top_splitter, 7)  # 上部分占70%
        main_layout.addWidget(bottom_widget, 3)  # 下部分占30%
        
    def create_toolbar(self):
        """创建工具栏，子类可以重写此方法"""
        return None
        
    def setup_file_list(self):
        """设置文件列表的基本属性"""
        # 设置表头
        self.file_list.setColumnCount(4)
        self.file_list.setHorizontalHeaderLabels(["文件名", "大小", "修改时间", "状态"])
        
        # 设置表头样式
        header = self.file_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 文件名列自适应宽度
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # 启用排序
        self.file_list.setSortingEnabled(True)
        
        # 设置选择模式
        self.file_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.file_list.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        
        # 启用拖放
        self.file_list.setAcceptDrops(True)
        self.file_list.dragEnterEvent = self.dragEnterEvent
        self.file_list.dropEvent = self.dropEvent
        
    def setup_settings_ui(self, layout):
        """设置右侧设置区域，子类必须重写此方法"""
        output_widget = QWidget()
        output_layout = QVBoxLayout(output_widget)
        
        # 输出位置单选按钮
        self.output_original = QRadioButton("原位置")
        self.output_custom = QRadioButton("自定义位置")
        self.output_original.setChecked(True)
        
        output_layout.addWidget(self.output_original)
        output_layout.addWidget(self.output_custom)
        
        # 自定义输出路径
        path_widget = QWidget()
        path_layout = QHBoxLayout()
        path_layout.setContentsMargins(20, 0, 0, 0)
        
        self.output_path = QLineEdit()
        self.output_path.setEnabled(False)
        self.output_path.setPlaceholderText("选择输出位置...")
        
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setEnabled(False)
        self.browse_btn.clicked.connect(self.browse_output_path)
        
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(self.browse_btn)
        
        path_widget.setLayout(path_layout)
        output_layout.addWidget(path_widget)
        
        # 输出文件夹名称
        name_widget = QWidget()
        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(20, 0, 0, 0)
        
        self.output_name = QLineEdit()
        self.output_name.setText("output")  # 默认值
        
        name_layout.addWidget(QLabel("输出文件夹"))
        name_layout.addWidget(self.output_name)
        
        name_widget.setLayout(name_layout)
        output_layout.addWidget(name_widget)
        
        # 连接信号
        self.output_original.toggled.connect(self.on_output_location_changed)
        self.output_custom.toggled.connect(self.on_output_location_changed)
        
        output_widget.setLayout(output_layout)
        layout.addWidget(output_widget)
        
    def on_output_location_changed(self, checked):
        """输出位置改变时的处理"""
        self.output_path.setEnabled(self.output_custom.isChecked())
        self.browse_btn.setEnabled(self.output_custom.isChecked())
        
    def browse_output_path(self):
        """浏览输出路径"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.output_path.setText(path)
            
    def get_output_config(self):
        """获取输出配置"""
        return {
            'use_original_location': self.output_original.isChecked(),
            'custom_output_path': self.output_path.text() if self.output_custom.isChecked() else None,
            'output_name': self.output_name.text()
        }
        
    def format_size(self, size):
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def add_file_to_list(self, file_path):
        """添加文件到列表"""
        row = self.file_list.rowCount()
        self.file_list.insertRow(row)
        
        # 文件名
        file_name = os.path.basename(file_path)
        name_item = QTableWidgetItem(file_name)
        self.file_list.setItem(row, 0, name_item)
        
        # 存储完整路径
        self.file_paths[row] = file_path
        
        # 文件大小
        size = os.path.getsize(file_path)
        size_str = self.format_size(size)
        self.file_list.setItem(row, 1, QTableWidgetItem(size_str))
        
        # 修改时间
        mtime = os.path.getmtime(file_path)
        date_time = QDateTime.fromSecsSinceEpoch(int(mtime))
        date_str = date_time.toString("yyyy-MM-dd hh:mm:ss")
        self.file_list.setItem(row, 2, QTableWidgetItem(date_str))
        
        # 状态
        self.file_list.setItem(row, 3, QTableWidgetItem("待处理"))
        
    def clear_file_list(self):
        """清空文件列表"""
        self.file_list.setRowCount(0)
        self.file_paths.clear()
        
    def remove_selected_files(self):
        """删除选中的文件"""
        rows = sorted(set(item.row() for item in self.file_list.selectedItems()), reverse=True)
        for row in rows:
            self.file_paths.pop(row, None)
            self.file_list.removeRow(row)
            
        # 重新映射行号和文件路径
        new_paths = {}
        for row in range(self.file_list.rowCount()):
            file_name = self.file_list.item(row, 0).text()
            for old_row, path in self.file_paths.items():
                if os.path.basename(path) == file_name:
                    new_paths[row] = path
                    break
        self.file_paths = new_paths
            
    def get_all_files(self):
        """获取列表中的所有文件路径"""
        return list(self.file_paths.values())
        
    def update_file_status(self, row, status):
        """更新文件状态"""
        if 0 <= row < self.file_list.rowCount():
            self.file_list.item(row, 3).setText(status)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        """处理拖入事件"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """处理放下事件"""
        urls = event.mimeData().urls()
        for url in urls:
            file_path = url.toLocalFile()
            if os.path.isfile(file_path):
                if self.is_valid_file(file_path):
                    self.add_file_to_list(file_path)
            elif os.path.isdir(file_path):
                self.add_files_from_folder(file_path)
                    
    def is_valid_file(self, file_path):
        """检查文件是否有效，子类需要重写此方法"""
        return True
        
    def add_files_from_folder(self, folder_path):
        """从文件夹添加文件，子类需要重写此方法"""
        pass
        
    def log_message(self, message):
        """添加日志消息"""
        self.log_text.append(message)
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
