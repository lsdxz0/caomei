from PIL import Image
import os
import threading
from typing import List, Dict, Optional, Callable
from queue import Queue
from utils import natural_sort_key

class ImageProcessor:
    def __init__(self):
        self.paused = False
        self.stopped = False
        self.current_thread = None
        self.processing_queue = Queue()
        # 添加线程控制事件
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.pause_event.set()  # 默认不暂停
        self.stop_event.clear()  # 默认不停止

    def split_images(self, files: List[str], input_root_dir: str, split_config: Dict, output_config: Dict,
                    progress_callback: Optional[Callable] = None,
                    log_callback: Optional[Callable] = None):
        """分割图片"""
        self.paused = False
        self.stopped = False
        self.pause_event.set()
        self.stop_event.clear()
        
        def process_worker():
            try:
                # 创建主输出目录
                if output_config['use_original_location']:
                    output_base = os.path.join(input_root_dir, output_config['output_name'])
                else:
                    output_base = os.path.join(output_config['custom_output_path'], output_config['output_name'])
                
                os.makedirs(output_base, exist_ok=True)
                
                if log_callback:
                    log_callback(f"创建输出目录: {output_base}")
                
                # 按文件夹分组文件
                folder_files = {}
                for file_path in files:
                    parent_dir = os.path.basename(os.path.dirname(file_path))
                    if parent_dir not in folder_files:
                        folder_files[parent_dir] = []
                    folder_files[parent_dir].append(file_path)
                
                # 计算总任务数
                total_tasks = sum(len(folder_files[folder]) for folder in folder_files)
                processed_tasks = 0
                
                # 处理每个文件夹
                for folder_name, folder_files_list in folder_files.items():
                    if self.stop_event.is_set():
                        if log_callback:
                            log_callback("处理已停止")
                        return
                    
                    # 创建文件夹输出目录
                    folder_output_dir = os.path.join(output_base, folder_name)
                    os.makedirs(folder_output_dir, exist_ok=True)
                    
                    if log_callback:
                        log_callback(f"处理文件夹: {folder_name}")
                    
                    # 处理文件夹中的每个文件
                    for index, file_path in enumerate(sorted(folder_files_list, key=lambda x: natural_sort_key(os.path.basename(x)))):
                        if self.stop_event.is_set():
                            if log_callback:
                                log_callback("处理已停止")
                            return
                        
                        self.pause_event.wait()
                        
                        try:
                            img_name = os.path.splitext(os.path.basename(file_path))[0]
                            
                            if log_callback:
                                log_callback(f"处理图片: {folder_name}/{img_name}")
                            
                            # 判断是否为首页
                            is_first_page = index == 0
                            
                            with Image.open(file_path) as img:
                                # 分割图片
                                if split_config['mode'] == 'custom':
                                    parts = self._split_image_custom(
                                        img, 
                                        split_config['target_width'],
                                        split_config['target_height'],
                                        split_config['rotate_bottom'],
                                        split_config['special_first'],
                                        is_first_page
                                    )
                                else:
                                    parts = self._split_image_general(
                                        img,
                                        split_config['rotate_bottom'],
                                        split_config['special_first'],
                                        is_first_page
                                    )
                                
                                # 保存分割后的图片
                                for i, part in enumerate(parts):
                                    output_path = os.path.join(folder_output_dir, f"{img_name}_split_{i+1}.jpg")
                                    part.save(output_path, "JPEG", quality=95)
                            
                            if log_callback:
                                log_callback(f"处理完成：{folder_name}/{img_name}")
                            
                            processed_tasks += 1
                            if progress_callback:
                                progress_callback(processed_tasks, total_tasks)
                            
                        except Exception as e:
                            if log_callback:
                                log_callback(f"处理失败：{folder_name}/{img_name} - {str(e)}")
                            continue
                
                if log_callback and not self.stop_event.is_set():
                    log_callback("处理完成")
                
            except Exception as e:
                if log_callback:
                    log_callback(f"处理过程发生错误: {str(e)}")
            finally:
                # 重置状态
                self.paused = False
                self.stopped = False
                self.pause_event.set()
                self.stop_event.clear()
        
        self.current_thread = threading.Thread(target=process_worker)
        self.current_thread.start()
    
    def _split_image_custom(self, img: Image.Image, target_width: int, target_height: int, 
                           rotate_bottom: bool, special_first: bool, is_first_page: bool) -> List[Image.Image]:
        """
        根据目标尺寸分割图片
        
        Args:
            img: 原始图片
            target_width: 目标宽度
            target_height: 目标高度
            rotate_bottom: 是否旋转下半部分（仅在横向分割时生效）
            special_first: 是否特殊处理第一张图片
            is_first_page: 是否为首页
            
        Returns:
            分割后的图片列表
        """
        width, height = img.size
        
        # 判断图片尺寸是否符合目标尺寸（允许10%的误差）
        width_ratio = abs(width / target_width - 1)
        height_ratio = abs(height / target_height - 1)
        
        if width_ratio <= 0.1 and height_ratio <= 0.1:
            # 符合目标尺寸，进行横向分割（horizontal split）
            # RAZ模式在这种情况下生效
            mid = height // 2
            top = img.crop((0, 0, width, mid))
            bottom = img.crop((0, mid, width, height))
            
            # RAZ模式：处理下半部分旋转
            if rotate_bottom and not (is_first_page and special_first):
                bottom = bottom.rotate(180)
                
            return [top, bottom]
        else:
            # 不符合目标尺寸，进行纵向分割（vertical split）
            mid = width // 2
            return [
                img.crop((0, 0, mid, height)),
                img.crop((mid, 0, width, height))
            ]
    
    def _split_image_general(self, img: Image.Image, rotate_bottom: bool, 
                            special_first: bool, is_first_page: bool) -> List[Image.Image]:
        """
        根据宽高比分割图片
        
        Args:
            img: 原始图片
            rotate_bottom: 是否旋转下半部分（仅在横向分割时生效）
            special_first: 是否特殊处理第一张图片
            is_first_page: 是否为首页
            
        Returns:
            分割后的图片列表
        """
        width, height = img.size
        
        # 通用模式：根据宽高比判断分割方向
        if width / height > 1.2:  
            # 纵向分割（vertical split）：从中间竖线分割
            mid = width // 2
            return [
                img.crop((0, 0, mid, height)),
                img.crop((mid, 0, width, height))
            ]
        elif height / width > 1.2:  
            # 横向分割（horizontal split）：从中间横线分割
            # RAZ模式在这种情况下生效
            mid = height // 2
            top = img.crop((0, 0, width, mid))
            bottom = img.crop((0, mid, width, height))
            
            # RAZ模式：处理下半部分旋转
            # 只有在不是首页，或者是首页但special_first为False时才旋转
            if rotate_bottom and not (is_first_page and special_first):
                bottom = bottom.rotate(180)
                
            return [top, bottom]
        else:
            # 接近正方形的图片不需要分割
            return [img]
    
    def pause(self):
        """暂停处理"""
        self.paused = True
        self.pause_event.clear()
        
    def resume(self):
        """继续处理"""
        self.paused = False
        self.pause_event.set()
        
    def stop(self):
        """停止处理"""
        self.stopped = True
        self.stop_event.set()
        if self.paused:
            self.resume()  # 如果暂停状态下停止，需要恢复以便线程可以退出
