from typing import Dict, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
import os

class FileSection:
    """文件区域类，代表一个大文件夹的文件列表"""
    def __init__(self, folder_path: str, name: str):
        self.folder_path = folder_path
        self.name = name
        self.files: Dict[str, List[Tuple[str, str]]] = defaultdict(list)  # 类型 -> [(路径, 名称), ...]
        self.statistics: Dict[str, int] = defaultdict(int)  # 类型 -> 数量
        self.total_files = 0
        self.total_size = 0
        self.is_expanded = True
    
    def add_file(self, file_path: str, file_type: str):
        """添加文件到区域"""
        name = os.path.basename(file_path)
        self.files[file_type].append((file_path, name))
        self.statistics[file_type] += 1
        self.total_files += 1
        if os.path.isfile(file_path):
            self.total_size += os.path.getsize(file_path)

    def get_statistics(self) -> str:
        """获取区域统计信息"""
        stats = [f"总文件数: {self.total_files}"]
        for file_type, count in self.statistics.items():
            stats.append(f"{file_type}: {count}")
        if self.total_size > 0:
            size_mb = self.total_size / (1024 * 1024)
            stats.append(f"总大小: {size_mb:.2f}MB")
        return " | ".join(stats)

class FileListManager:
    """文件列表管理器"""
    def __init__(self):
        self.sections: Dict[str, FileSection] = {}
        self.supported_types = {
            # 文档类型
            '.pdf': 'PDF文档',
            '.doc': 'Word文档',
            '.docx': 'Word文档',
            '.txt': '文本文件',
            # 媒体类型
            '.mp4': '视频文件',
            '.avi': '视频文件',
            '.mkv': '视频文件',
            '.mp3': '音频文件',
            '.wav': '音频文件',
            '.flac': '音频文件',
            # 图片类型
            '.jpg': '图片文件',
            '.jpeg': '图片文件',
            '.png': '图片文件',
            '.gif': '图片文件',
            # 压缩文件
            '.zip': '压缩文件',
            '.rar': '压缩文件',
            '.7z': '压缩文件'
        }
    
    def create_section(self, folder_path: str, name: Optional[str] = None) -> FileSection:
        """创建新的文件区域"""
        if name is None:
            name = os.path.basename(folder_path)
        section = FileSection(folder_path, name)
        self.sections[folder_path] = section
        return section

    def scan_folder(self, folder_path: str, name: Optional[str] = None) -> FileSection:
        """扫描文件夹并创建区域"""
        section = self.create_section(folder_path, name)
        
        if not os.path.exists(folder_path):
            return section
            
        for root, dirs, files in os.walk(folder_path):
            # 处理文件
            for file_name in files:
                file_path = os.path.join(root, file_name)
                ext = os.path.splitext(file_name)[1].lower()
                if ext in self.supported_types:
                    file_type = self.supported_types[ext]
                    section.add_file(file_path, file_type)
            
            # 处理目录
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                section.add_file(dir_path, "文件夹")
        
        return section

    def get_section_info(self, section_name: str) -> str:
        """获取区域信息"""
        section = self.sections.get(section_name)
        if not section:
            return "区域不存在"
        
        info = [f"=== {section.name} ==="]
        info.append(section.get_statistics())
        
        for file_type in sorted(section.files.keys()):
            files = section.files[file_type]
            info.append(f"\n{file_type} ({len(files)}):")
            for _, name in sorted(files):
                info.append(f"  - {name}")
        
        return "\n".join(info)

    def get_all_sections_info(self) -> str:
        """获取所有区域信息"""
        return "\n\n".join(
            self.get_section_info(section_name)
            for section_name in self.sections
        )

    def search_files(self, keyword: str) -> Dict[str, List[Tuple[str, str]]]:
        """搜索文件
        返回: {区域名称: [(文件路径, 文件名称), ...], ...}
        """
        results = defaultdict(list)
        for section_name, section in self.sections.items():
            for files in section.files.values():
                for path, name in files:
                    if keyword.lower() in name.lower():
                        results[section.name].append((path, name))
        return results

    def filter_by_type(self, file_type: str) -> Dict[str, List[Tuple[str, str]]]:
        """按文件类型过滤
        返回: {区域名称: [(文件路径, 文件名称), ...], ...}
        """
        results = defaultdict(list)
        for section_name, section in self.sections.items():
            if file_type in section.files:
                results[section.name].extend(
                    [(path, name) for path, name in section.files[file_type]]
                )
        return results

    def get_section_types(self, section_name: str) -> List[str]:
        """获取区域中的文件类型列表"""
        section = self.sections.get(section_name)
        if not section:
            return []
        return sorted(section.files.keys())

    def toggle_section(self, section_name: str) -> bool:
        """切换区域的展开/折叠状态"""
        section = self.sections.get(section_name)
        if not section:
            return False
        section.is_expanded = not section.is_expanded
        return section.is_expanded

# 使用示例
if __name__ == "__main__":
    manager = FileListManager()
    
    # 扫描多个文件夹
    section1 = manager.scan_folder("path/to/videos", "视频文件夹")
    section2 = manager.scan_folder("path/to/music", "音频文件夹")
    section3 = manager.scan_folder("path/to/images", "图片文件夹")
    
    # 获取所有区域信息
    print(manager.get_all_sections_info())
    
    # 搜索文件
    results = manager.search_files("test")
    for section_name, files in results.items():
        print(f"\n在 {section_name} 中找到:")
        for _, name in files:
            print(f"  - {name}")
    
    # 按类型过滤
    video_files = manager.filter_by_type("视频文件")
    for section_name, files in video_files.items():
        print(f"\n{section_name} 中的视频文件:")
        for _, name in files:
            print(f"  - {name}")
