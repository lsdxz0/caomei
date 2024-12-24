from PyQt6.QtWidgets import (QMainWindow, QWidget, QTabWidget, QVBoxLayout, 
                                 QHBoxLayout, QTableWidget, QGroupBox, QPushButton, 
                                 QProgressBar, QTextEdit, QSplitter)
from PyQt6.QtCore import Qt
from .tab_pdf import PDFTab
from .tab_image import ImageTab
from .tab_merge import MergeTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("草莓阅读营-公众号助手")
        self.setMinimumSize(1000, 700)  # 设置最小窗口尺寸
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(PDFTab(), "PDF转图片")
        self.tab_widget.addTab(ImageTab(), "图片分割")
        self.tab_widget.addTab(MergeTab(), "文件合并")
        
        main_layout.addWidget(self.tab_widget)
