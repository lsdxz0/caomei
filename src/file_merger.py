import os
import shutil
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Union, Callable
import hashlib
import time
from queue import Queue
from utils import natural_sort_key
import threading

class FileMerger:
    def __init__(self):
        self.paused = False
        self.stopped = False
        self.operation_history = []
        # 添加线程控制事件
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.pause_event.set()  # 默认不暂停
        self.stop_event.clear()  # 默认不停止
        
        self.SUPPORTED_EXTENSIONS = {
            # 文本文件
            '.txt', '.doc', '.docx', '.pdf',
            # 图片文件
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
            # 音频文件
            '.mp3', '.wav', '.flac', '.m4a', '.aac', '.wma',
            # 视频文件
            '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'
        }
        self.IMAGE_EXTENSIONS = {
            # 图片文件
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp',
        }
        
    def pause(self):
        """暂停合并过程"""
        self.paused = True
        self.pause_event.clear()
        
    def resume(self):
        """继续合并过程"""
        self.paused = False
        self.pause_event.set()
        
    def stop(self):
        """停止合并过程"""
        self.stopped = True
        self.stop_event.set()
        if self.paused:
            self.resume()  # 如果暂停状态下停止，需要恢复以便线程可以退出
        
    def merge_files(self, input_folders: List[str], min_match: int = 2,
                   output_location: str = "原位置", custom_output_path: str = None,
                   output_name: str = None,
                   progress_callback: Callable[[int], None] = None, log_callback: Callable[[str], None] = None):
        """收集并整理文件"""
        try:
            # 初始化进度和状态
            self.paused = False
            self.stopped = False
            
            # 创建主输出目录
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            if output_location == "自定义位置" and custom_output_path:
                base_output_dir = custom_output_path
            else:
                base_output_dir = os.path.join(os.path.dirname(input_folders[0]))
            
            # 创建以output_name命名的母文件夹
            output_dir = os.path.join(base_output_dir, 
                                    output_name or f"收集文件_{timestamp}")
            os.makedirs(output_dir, exist_ok=True)
            
            if log_callback:
                log_callback(f"创建输出目录: {output_dir}")
            
            # 扫描所有文件夹
            all_files = defaultdict(list)
            for folder in input_folders:
                if self.stopped:
                    break
                folder_files = self.scan_folder(folder)
                for base_name, files in folder_files.items():
                    all_files[base_name].extend(files)
            
            # 过滤掉匹配数小于min_match的组
            filtered_files = {
                base_name: files
                for base_name, files in all_files.items()
                if len(files) >= min_match
            }
            
            if not filtered_files:
                if log_callback:
                    log_callback("未找到满足条件的文件组")
                return
            
            # 计算总文件数用于进度显示
            total_files = sum(len(files) for files in filtered_files.values())
            processed_files = 0
            
            # 处理每个文件组
            for base_name, files in filtered_files.items():
                if self.stopped:
                    break
                
                while self.paused:
                    time.sleep(0.1)
                
                # 创建组目录
                group_dir = os.path.join(output_dir, base_name)
                os.makedirs(group_dir, exist_ok=True)
                
                # 记录已处理的哈希值，用于去重
                processed_hashes = set()
                processed_folders = set()
                
                # 先处理根目录文件
                root_files = [f for f in files if f['type'] == 'root_file']
                root_files.sort(key=lambda x: natural_sort_key(os.path.basename(x['path'])))
                
                for file_item in root_files:
                    if self.stopped:
                        break
                    
                    while self.paused:
                        time.sleep(0.1)
                    
                    try:
                        file_path = file_item['path']
                        file_hash = self.calculate_file_hash(file_path)
                        
                        if file_hash in processed_hashes:
                            if log_callback:
                                log_callback(f"跳过重复文件: {file_item['name']}")
                            continue
                        
                        processed_hashes.add(file_hash)
                        target_path = os.path.join(group_dir, file_item['name'])
                        
                        # 处理文件名冲突
                        counter = 1
                        while os.path.exists(target_path):
                            name, ext = os.path.splitext(file_item['name'])
                            target_path = os.path.join(group_dir, f"{name}_{counter}{ext}")
                            counter += 1
                        
                        shutil.copy2(file_path, target_path)
                        if log_callback:
                            log_callback(f"已复制根目录文件: {file_item['name']}")
                        
                        processed_files += 1
                        if progress_callback:
                            progress = int((processed_files / total_files) * 100)
                            progress_callback(progress)
                    
                    except Exception as e:
                        if log_callback:
                            log_callback(f"处理文件时出错 {file_item['name']}: {str(e)}")
                
                # 处理子文件夹文件和图片文件夹
                other_files = [f for f in files if f['type'] in ('subfolder_file', 'image_folder')]
                other_files.sort(key=lambda x: natural_sort_key(os.path.basename(x['path'])))
                
                for file_item in other_files:
                    if self.stopped:
                        break
                    
                    while self.paused:
                        time.sleep(0.1)
                    
                    try:
                        if file_item['type'] == 'image_folder':
                            folder_path = file_item['path']
                            if folder_path in processed_folders:
                                continue
                            
                            # 创建目标文件夹，保持相对路径结构
                            target_folder = os.path.join(group_dir, file_item['rel_path'])
                            if os.path.exists(target_folder):
                                counter = 1
                                while os.path.exists(target_folder):
                                    parent_dir = os.path.dirname(target_folder)
                                    folder_name = os.path.basename(target_folder)
                                    target_folder = os.path.join(parent_dir, f"{folder_name}_{counter}")
                                    counter += 1
                            
                            shutil.copytree(folder_path, target_folder)
                            processed_folders.add(folder_path)
                            
                            if log_callback:
                                log_callback(f"已复制图片文件夹: {file_item['name']}")
                        
                        else:  # subfolder_file
                            file_path = file_item['path']
                            file_hash = self.calculate_file_hash(file_path)
                            
                            if file_hash in processed_hashes:
                                if log_callback:
                                    log_callback(f"跳过重复文件: {file_item['name']}")
                                continue
                            
                            processed_hashes.add(file_hash)
                            
                            # 创建目标文件夹，保持相对路径结构
                            target_dir = os.path.join(group_dir, file_item['rel_path'])
                            os.makedirs(target_dir, exist_ok=True)
                            
                            target_path = os.path.join(target_dir, file_item['name'])
                            
                            # 处理文件名冲突
                            counter = 1
                            while os.path.exists(target_path):
                                name, ext = os.path.splitext(file_item['name'])
                                target_path = os.path.join(target_dir, f"{name}_{counter}{ext}")
                                counter += 1
                            
                            shutil.copy2(file_path, target_path)
                            if log_callback:
                                log_callback(f"已复制子文件夹文件: {file_item['name']}")
                        
                        processed_files += 1
                        if progress_callback:
                            progress = int((processed_files / total_files) * 100)
                            progress_callback(progress)
                    
                    except Exception as e:
                        if log_callback:
                            log_callback(f"处理文件时出错 {file_item['name']}: {str(e)}")
            
            if log_callback:
                if self.stopped:
                    log_callback("操作已停止")
                else:
                    log_callback("文件收集完成")
        
        except Exception as e:
            if log_callback:
                log_callback(f"发生错误: {str(e)}")
                
    def scan_folder(self, folder_path: str) -> Dict[str, List[Union[str, Dict[str, str]]]]:
        """扫描文件夹，返回按类型分组的文件列表"""
        files_by_type = defaultdict(list)
        
        for root, dirs, files in os.walk(folder_path):
            # 获取相对于根目录的路径
            rel_path = os.path.relpath(root, folder_path)
            
            # 处理根目录文件
            if rel_path == '.':
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in self.SUPPORTED_EXTENSIONS:
                        base_name = os.path.splitext(file)[0]
                        file_path = os.path.join(root, file)
                        files_by_type[base_name].append({
                            'type': 'root_file',
                            'path': file_path,
                            'name': file
                        })
            else:
                # 处理子文件夹中的文件
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in self.SUPPORTED_EXTENSIONS:
                        # 使用当前文件夹名作为分组依据
                        folder_name = os.path.basename(root)
                        file_path = os.path.join(root, file)
                        files_by_type[folder_name].append({
                            'type': 'subfolder_file',
                            'path': file_path,
                            'name': file,
                            'rel_path': rel_path
                        })
        
        return files_by_type
        
    def calculate_file_hash(self, file_path: str, block_size: int = 65536) -> str:
        """计算文件的MD5哈希值，用于文件去重"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(block_size), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def create_backup(self, file_path: str) -> str:
        """创建文件备份"""
        backup_path = file_path + '.bak'
        shutil.copy2(file_path, backup_path)
        return backup_path
        
    def undo_last_operation(self) -> bool:
        """撤销最后一次操作"""
        if self.operation_history:
            operation = self.operation_history.pop()
            if operation['action'] == 'backup':
                shutil.move(operation['backup'], operation['original'])
                return True
        return False
