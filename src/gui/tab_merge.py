from PyQt6.QtWidgets import (QToolBar, QPushButton, QSpinBox,
                           QLabel, QRadioButton, QFileDialog,
                           QVBoxLayout, QHBoxLayout, QWidget,
                           QLineEdit, QMessageBox, QGroupBox,
                           QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QObject, QDateTime
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from file_merger import FileMerger
from .base_tab import BaseTab

class MergeWorker(QObject):
    """文件合并工作线程"""
    finished = pyqtSignal()
    progress = pyqtSignal(int)
    error = pyqtSignal(str)
    log = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.merger = FileMerger()
        self.input_folders = []
        self.min_match = 2
        self.output_location = "原位置"
        self.custom_output_path = None
        self.output_name = None
        self.is_completed = False
        
    def configure(self, input_folders, min_match, output_location, custom_output_path, output_name=None):
        self.input_folders = input_folders
        self.min_match = min_match
        self.output_location = output_location
        self.custom_output_path = custom_output_path
        self.output_name = output_name
        self.is_completed = False
        # 确保merger已初始化
        if not hasattr(self, 'merger') or self.merger is None:
            self.merger = FileMerger()
        
    def process(self):
        try:
            def progress_callback(value):
                self.progress.emit(value)
                
            def log_callback(msg):
                self.log.emit(msg)
                if msg == "文件收集完成":
                    self.is_completed = True
                    self.finished.emit()
                
            self.merger.merge_files(
                input_folders=self.input_folders,
                min_match=self.min_match,
                output_location=self.output_location,
                custom_output_path=self.custom_output_path,
                output_name=self.output_name,  # 添加输出文件夹名称
                progress_callback=progress_callback,
                log_callback=log_callback
            )
            
        except Exception as e:
            self.error.emit(str(e))

class MergeTab(BaseTab):
    # 定义信号
    processing_started = pyqtSignal()
    processing_finished = pyqtSignal()
    processing_paused = pyqtSignal()
    processing_stopped = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.is_processing = False
        self.is_paused = False
        
        # 创建worker和线程
        self.worker = MergeWorker()
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
        
    def create_toolbar(self):
        """创建工具栏"""
        toolbar = QToolBar()
        
        # 添加文件夹按钮
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        toolbar.addWidget(self.add_folder_btn)
        
        toolbar.addSeparator()
        
        # 清空列表按钮
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_file_list)
        toolbar.addWidget(self.clear_btn)
        
        # 删除选中按钮
        self.remove_btn = QPushButton("删除选中")
        self.remove_btn.clicked.connect(self.remove_selected_files)
        toolbar.addWidget(self.remove_btn)
        
        return toolbar
        
    def setup_settings_ui(self, layout):
        """设置界面"""
        # 最少匹配数设置
        match_group = QGroupBox("匹配设置")
        match_layout = QVBoxLayout()
        
        match_widget = QWidget()
        match_widget_layout = QHBoxLayout()
        match_widget_layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_match_spin = QSpinBox()
        self.min_match_spin.setRange(2, 10)
        self.min_match_spin.setValue(2)
        self.min_match_spin.setSuffix(" 个")
        
        match_widget_layout.addWidget(QLabel("最少匹配数"))
        match_widget_layout.addWidget(self.min_match_spin)
        match_widget_layout.addStretch()
        
        match_widget.setLayout(match_widget_layout)
        match_layout.addWidget(match_widget)
        match_group.setLayout(match_layout)
        layout.addWidget(match_group)
        
        # 输出设置（使用基类的设置）
        output_group = QGroupBox("输出设置")
        output_layout = QVBoxLayout()
        super().setup_settings_ui(output_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # 设置默认输出文件夹名
        self.output_name.setText("merged_files")
        
        layout.addStretch()
        
    def add_folder(self):
        """添加文件夹"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            self.add_file_to_list(folder)
            
    def start_processing(self):
        """开始处理"""
        if self.file_list.topLevelItemCount() == 0:
            QMessageBox.warning(self, "警告", "请先添加需要处理的文件夹！")
            return
            
        if self.output_custom.isChecked() and not self.output_path.text():
            QMessageBox.warning(self, "警告", "请选择输出目录！")
            return
            
        self.is_processing = True
        self.is_paused = False
        self.update_control_buttons()
        
        # 收集处理参数
        input_folders = []
        for i in range(self.file_list.topLevelItemCount()):
            if i in self.file_paths:
                input_folders.append(self.file_paths[i])
        
        try:
            # 如果线程在运行，先停止它
            if self.thread.isRunning():
                self.thread.quit()
                self.thread.wait()
            
            # 配置worker
            self.worker.configure(
                input_folders=input_folders,
                min_match=self.min_match_spin.value(),
                output_location="原位置" if self.output_original.isChecked() else "自定义位置",
                custom_output_path=self.output_path.text() if self.output_custom.isChecked() else None,
                output_name=self.output_name.text()  # 添加输出文件夹名称
            )
            
            # 重置状态
            if not hasattr(self.worker.merger, 'stop_event'):
                self.worker.merger = FileMerger()
            self.worker.merger.stop_event.clear()
            self.worker.merger.pause_event.set()
            
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
            QMessageBox.information(self, "完成", "文件合并已完成！")
        
    def pause_processing(self):
        """暂停处理"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.worker.merger.pause_event.clear()
            self.pause_button.setText("继续")
            self.processing_paused.emit()
        else:
            self.worker.merger.pause_event.set()
            self.pause_button.setText("暂停")
        self.update_control_buttons()
        
    def stop_processing(self):
        """停止处理"""
        if self.thread.isRunning():
            # 设置停止标志
            self.worker.merger.stop_event.set()
            
            # 如果当前是暂停状态，需要恢复以便能够退出
            if self.is_paused:
                self.worker.merger.pause_event.set()
            
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
        
    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)
        
        # 只在真正完成时更新状态
        if value == 100 and self.worker.is_completed:
            self.is_processing = False
            self.update_control_buttons()
            self.processing_finished.emit()
            QMessageBox.information(self, "完成", "文件合并已完成！")

    def setup_file_list(self):
        """设置文件列表"""
        # 使用QTreeWidget替代QTableWidget
        self.file_list = QTreeWidget()
        self.file_list.setHeaderLabels(["文件夹/文件", "大小", "修改时间", "状态"])
        
        # 设置列宽
        self.file_list.setColumnWidth(0, 300)  # 文件名列宽
        self.file_list.setColumnWidth(1, 100)  # 大小列宽
        self.file_list.setColumnWidth(2, 150)  # 时间列宽
        
        # 允许多选
        self.file_list.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        
    def add_file_to_list(self, folder_path):
        """添加文件夹到列表"""
        # 创建根节点（源文件夹）
        folder_name = os.path.basename(folder_path)
        root_item = QTreeWidgetItem(self.file_list)
        root_item.setText(0, folder_name)
        root_item.setText(1, self.get_folder_size(folder_path))
        root_item.setText(2, self.get_modify_time(folder_path))
        root_item.setText(3, "待处理")
        
        # 添加子项
        self.add_folder_items(root_item, folder_path)
        
        # 存储完整路径
        self.file_paths[self.file_list.indexOfTopLevelItem(root_item)] = folder_path
        
    def add_folder_items(self, parent_item, folder_path):
        """递归添加文件夹内容"""
        try:
            # 获取文件夹内容
            items = os.listdir(folder_path)
            
            # 分别处理文件和文件夹
            folders = []
            files = []
            for item in items:
                item_path = os.path.join(folder_path, item)
                if os.path.isdir(item_path):
                    folders.append(item)
                else:
                    files.append(item)
            
            # 先添加文件夹
            for folder in sorted(folders):
                folder_path_full = os.path.join(folder_path, folder)
                folder_item = QTreeWidgetItem(parent_item)
                folder_item.setText(0, folder)
                folder_item.setText(1, self.get_folder_size(folder_path_full))
                folder_item.setText(2, self.get_modify_time(folder_path_full))
                
                # 递归添加子文件夹内容
                self.add_folder_items(folder_item, folder_path_full)
            
            # 再添加文件
            for file in sorted(files):
                file_path_full = os.path.join(folder_path, file)
                file_item = QTreeWidgetItem(parent_item)
                file_item.setText(0, file)
                file_item.setText(1, self.get_file_size(file_path_full))
                file_item.setText(2, self.get_modify_time(file_path_full))
                
        except Exception as e:
            self.log_message(f"添加文件夹内容时出错: {str(e)}")
            
    def get_folder_size(self, folder_path):
        """获取文件夹大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return self.format_size(total_size)
        
    def get_file_size(self, file_path):
        """获取文件大小"""
        return self.format_size(os.path.getsize(file_path))
        
    def get_modify_time(self, path):
        """获取修改时间"""
        timestamp = os.path.getmtime(path)
        return QDateTime.fromSecsSinceEpoch(int(timestamp)).toString("yyyy-MM-dd hh:mm:ss")
        
    def clear_file_list(self):
        """清空文件列表"""
        self.file_list.clear()
        self.file_paths.clear()
        
    def remove_selected_files(self):
        """删除选中项"""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            # 如果是顶层目，需要更新file_paths
            if item.parent() is None:
                index = self.file_list.indexOfTopLevelItem(item)
                if index in self.file_paths:
                    del self.file_paths[index]
            
            # 删除项目
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.file_list.indexOfTopLevelItem(item)
                self.file_list.takeTopLevelItem(index)
        
        # 重新整理file_paths的索引
        new_file_paths = {}
        for i in range(self.file_list.topLevelItemCount()):
            item = self.file_list.topLevelItem(i)
            old_index = self.file_list.indexOfTopLevelItem(item)
            if old_index in self.file_paths:
                new_file_paths[i] = self.file_paths[old_index]
        self.file_paths = new_file_paths
