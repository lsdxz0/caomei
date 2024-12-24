import os
import fitz
from PIL import Image
from datetime import datetime
import threading
import queue
from typing import List, Dict, Optional, Callable
from utils import natural_sort_key

class PDFProcessor:
    def __init__(self):
        self.processing = False
        self.paused = False
        self.stopped = False
        # 添加线程控制事件
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.pause_event.set()  # 默认不暂停
        self.stop_event.clear()  # 默认不停止
        
    def process_files(self, files: List[str], dpi: int, output_format: str,
                     interval: int, output_location: str, custom_output_path: str = None,
                     split_config: Dict = None, progress_callback: Callable = None, log_callback: Callable = None):
        """
        处理PDF文件列表
        
        Args:
            files: PDF文件路径列表
            dpi: 输出图片DPI
            output_format: 输出格式 ('PNG' 或 'JPG')
            interval: 处理间隔 (0表示处理所有PDF，1表示隔一个处理一个，以此类推)
            output_location: 输出位置 ('原位置' 或 '自定义位置')
            custom_output_path: 自定义输出路径
            split_config: 图片分割配置
            progress_callback: 进度回调函数
            log_callback: 日志回调函数
        """
        try:
            # 确保split_config存在
            split_config = split_config or {}
            output_name = split_config.get('output_name', 'pdf_output')
            
            # 创建主输出目录
            if output_location == "原位置":
                base_dir = os.path.dirname(files[0])
                output_base = os.path.join(base_dir, output_name)
            else:
                output_base = os.path.join(custom_output_path, output_name)
            
            # 创建主输出目录
            os.makedirs(output_base, exist_ok=True)
            
            if log_callback:
                log_callback(f"创建输出目录: {output_base}")
            
            # 根据间隔选择要处理的文件
            step = 1 if interval == 0 else interval + 1
            files_to_process = files[::step]
            total_files = len(files_to_process)
            total_pages = sum(fitz.open(f).page_count for f in files_to_process)
            processed_pages = 0
            
            # 处理每个文件
            for file_index, file_path in enumerate(files_to_process):
                if self.stopped:
                    if log_callback:
                        log_callback("处理已停止")
                    return
                        
                if not os.path.exists(file_path):
                    if log_callback:
                        log_callback(f"文件不存在: {file_path}")
                    continue
                    
                try:
                    # 打开PDF文件
                    doc = fitz.open(file_path)
                    doc_pages = doc.page_count
                    
                    # 为当前PDF创建输出子目录
                    pdf_name = os.path.splitext(os.path.basename(file_path))[0]
                    pdf_output_dir = os.path.join(output_base, pdf_name)
                    os.makedirs(pdf_output_dir, exist_ok=True)
                    
                    if log_callback:
                        log_callback(f"处理PDF: {pdf_name}")
                        log_callback(f"输出目录: {pdf_output_dir}")
                    
                    # 处理每一页
                    for page_num in range(doc_pages):
                        if self.stopped:
                            if log_callback:
                                log_callback("处理已停止")
                            return
                            
                        # 使用pause_event等待而不是循环检查
                        self.pause_event.wait()
                        if self.stopped:
                            if log_callback:
                                log_callback("处理已停止")
                            return
                            
                        try:
                            page = doc.load_page(page_num)
                            pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                                
                            # 设置输出文件名
                            output_file = os.path.join(
                                pdf_output_dir, 
                                f"page_{page_num + 1}.{output_format.lower()}"
                            )
                                
                            # 保存图片
                            if output_format.lower() == "png":
                                pix.save(output_file)
                            else:  # jpg
                                pix.pil_save(output_file, "JPEG")
                                
                            # 更新进度
                            processed_pages += 1
                            if progress_callback:
                                progress = (processed_pages / total_pages) * 100
                                progress_callback(int(progress))
                                
                            if log_callback:
                                log_callback(f"已处理: {pdf_name} - 第 {page_num + 1} 页")
                                    
                        except Exception as e:
                            if log_callback:
                                log_callback(f"处理页面时发生错误: {str(e)}")
                            continue
                        
                    doc.close()
                        
                except Exception as e:
                    if log_callback:
                        log_callback(f"处理文件时发生错误: {str(e)}")
                    continue
                
            if progress_callback:
                progress_callback(100)
            if log_callback:
                log_callback("处理完成")
                    
        except Exception as e:
            if log_callback:
                log_callback(f"处理过程发生错误: {str(e)}")
            raise
        finally:
            self.processing = False

    def split_image(self, img: Image.Image, is_first_page: bool, config: Dict, log_callback: Callable = None) -> List[Image.Image]:
        """
        根据配置分割图片
        
        Args:
            img: 原始图片
            is_first_page: 是否是PDF的第一页
            config: 分割��置
            log_callback: 日志回调函数
            
        Returns:
            分割后的图片列表
        """
        try:
            # 验证图片
            if not isinstance(img, Image.Image):
                if log_callback:
                    log_callback("错误：无效的图片对象")
                raise ValueError("无效的图片对象")
                
            # 检查图片大小
            width, height = img.size
            if log_callback:
                log_callback(f"图片尺寸: {width}x{height}")
                
            if width * height > 100000000:  # 限制图片大小约为100M像素
                if log_callback:
                    log_callback(f"错误：图片太大: {width}x{height}")
                raise ValueError(f"图片太大: {width}x{height}")
                
            # 通用模式：根据宽高比判断分割方向
            if config['mode'] == "通用模式":
                if log_callback:
                    log_callback(f"使用通用模式，分割比例: {config.get('split_ratio', 1.2)}")
                    
                ratio = config.get('split_ratio', 1.2)  # 可配置的分割比例
                if width / height > ratio:  # 左右分割
                    if log_callback:
                        log_callback("检测为横向图片，进行左右分割")
                    mid = width // 2
                    left = img.crop((0, 0, mid, height))
                    right = img.crop((mid, 0, width, height))
                    if log_callback:
                        log_callback(f"分割完成：左侧 {mid}x{height}, 右侧 {width-mid}x{height}")
                    return [left, right]
                elif height / width > ratio:  # 上下分割
                    if log_callback:
                        log_callback("检测为纵向图片，进行上下分割")
                    mid = height // 2
                    top = img.crop((0, 0, width, mid))
                    bottom = img.crop((0, mid, width, height))
                    
                    # 处理下半部分旋转
                    should_rotate = config.get('rotate_bottom', False)
                    is_first_no_rotate = is_first_page and config.get('first_page_no_rotate', True)
                    
                    if should_rotate and not is_first_no_rotate:
                        if log_callback:
                            log_callback("旋转下半部分180度")
                        bottom = bottom.rotate(180)
                    
                    if log_callback:
                        log_callback(f"分割完成：上部 {width}x{mid}, 下部 {width}x{height-mid}")
                    return [top, bottom]
                else:  # 不需要分割
                    if log_callback:
                        log_callback("图片比例正常，无需分割")
                    return [img.copy()]  # 返回副本避免原图被修改
                    
            # 自定义模式：根据目标尺寸判断
            else:
                if 'target_width' not in config or 'target_height' not in config:
                    if log_callback:
                        log_callback("错误：自定义模式需要指定目标尺寸")
                    raise ValueError("自定义模式需要指定目标尺寸")
                    
                target_width = config['target_width']
                target_height = config['target_height']
                
                if log_callback:
                    log_callback(f"使用自定义模式，目标尺寸: {target_width}x{target_height}")
                
                # 计算当前图片与目标尺寸的比例
                width_ratio = width / target_width
                height_ratio = height / target_height
                
                # 允许的误差范围
                tolerance = config.get('size_tolerance', 0.1)  # 10%的误差
                
                if abs(1 - width_ratio) <= tolerance and abs(1 - height_ratio) <= tolerance:
                    if log_callback:
                        log_callback("图片符合目标尺寸，进行竖向分割")
                    # 符合目标尺寸，竖向分割
                    mid = height // 2
                    top = img.crop((0, 0, width, mid))
                    bottom = img.crop((0, mid, width, height))
                    
                    # 处理下半部分旋转
                    should_rotate = config.get('rotate_bottom', False)
                    is_first_no_rotate = is_first_page and config.get('first_page_no_rotate', True)
                    
                    if should_rotate and not is_first_no_rotate:
                        if log_callback:
                            log_callback("旋转下半部分180度")
                        bottom = bottom.rotate(180)
                    
                    if log_callback:
                        log_callback(f"分割完成：上部 {width}x{mid}, 下部 {width}x{height-mid}")
                    return [top, bottom]
                else:
                    if log_callback:
                        log_callback("图片不符合目标尺寸，进行横向分割")
                    # 不符合目标尺寸，横向分割
                    mid = width // 2
                    left = img.crop((0, 0, mid, height))
                    right = img.crop((mid, 0, width, height))
                    if log_callback:
                        log_callback(f"分割完成：左侧 {mid}x{height}, 右侧 {width-mid}x{height}")
                    return [left, right]
                    
        except Exception as e:
            if log_callback:
                log_callback(f"错误：图片分割失败: {str(e)}")
            raise ValueError(f"图片分割失败: {str(e)}")

    def split_images(self, files: List[str], split_config: Dict,
                    output_location: str, custom_output_path: str = None,
                    output_folder_name: str = None,
                    progress_callback: Callable = None, log_callback: Callable = None):
        """
        批量分割图片
        
        Args:
            files: 要处理的图片文件列表
            split_config: 分割配置
            output_location: 输出位置
            custom_output_path: 自定义输出路径
            output_folder_name: 输出文件夹名称
            progress_callback: 进度回调
            log_callback: 日志回调
        """
        try:
            # 首先显示输出目录信息
            if output_location == "原位置":
                if log_callback:
                    log_callback("输出位置: 与原始文件相同目录")
            else:
                if log_callback:
                    log_callback(f"输出位置: {os.path.join(custom_output_path, output_folder_name)}")
            
            if log_callback:
                log_callback("-" * 50)
            
            # 获取输入文件夹的名称
            input_folder = os.path.basename(os.path.dirname(files[0]))
            if log_callback:
                log_callback(f"输入文件夹: {input_folder}")
                log_callback(f"总文件: {len(files)}")
                log_callback("-" * 50)
            
            # 使用自然排序
            files.sort(key=lambda x: natural_sort_key(os.path.basename(x)))
            
            total_files = len(files)
            processed_files = 0
            
            for file_index, file_path in enumerate(files):
                if self.stop_event.is_set():
                    if log_callback:
                        log_callback("处理已停止")
                    return
                    
                if not os.path.exists(file_path):
                    if log_callback:
                        log_callback(f"文件不存在: {file_path}")
                    continue
                    
                try:
                    # 使用with语句安全打开图片
                    with Image.open(file_path) as img:
                        if log_callback:
                            log_callback(f"\n正在处理: {os.path.basename(file_path)}")
                            log_callback(f"图片信息: 大小={img.size}, 格式={img.format}")
                            
                        # 确定输出目录
                        if output_location == "原位置":
                            # ��取相对路径
                            common_prefix = os.path.commonpath([os.path.dirname(f) for f in files])
                            rel_path = os.path.relpath(os.path.dirname(file_path), common_prefix)
                            output_dir = os.path.join(os.path.dirname(file_path), output_folder_name or "split_output")
                        else:
                            # 获取相对路径
                            common_prefix = os.path.commonpath([os.path.dirname(f) for f in files])
                            rel_path = os.path.relpath(os.path.dirname(file_path), common_prefix)
                            output_dir = os.path.join(custom_output_path, rel_path, output_folder_name or "split_output")
                        
                        # 创建输出目录
                        os.makedirs(output_dir, exist_ok=True)
                        
                        if log_callback:
                            log_callback(f"输出目录: {output_dir}")
                        
                        # 判断是否为首页
                        is_first_page = file_index == 0
                        if log_callback and is_first_page:
                            log_callback("这是首页，底部不会旋转")
                        
                        try:
                            split_images = self.split_image(img, is_first_page, split_config, log_callback)
                            if log_callback:
                                log_callback(f"分割结果: 将分割为 {len(split_images)} 个图片")
                            
                            # 保存分割后的图片
                            base_name = os.path.splitext(os.path.basename(file_path))[0]
                            for i, split_img in enumerate(split_images):
                                output_path = os.path.join(
                                    output_dir,
                                    f"{base_name}_split_{i + 1}.{split_img.format or 'PNG'}"
                                )
                                split_img.save(output_path)
                                if log_callback:
                                    log_callback(f"已保存: {os.path.basename(output_path)}")
                            
                            processed_files += 1
                            if progress_callback:
                                progress = (processed_files / total_files) * 100
                                progress_callback(int(progress))
                                
                        except Exception as e:
                            if log_callback:
                                log_callback(f"分割图片时发生错误: {str(e)}")
                            continue
                        
                except Exception as e:
                    if log_callback:
                        log_callback(f"处理文件时发生错误: {str(e)}")
                    continue
                    
                if log_callback:
                    log_callback(f"处理进度: {processed_files}/{total_files}")
                    log_callback("-" * 30)
            
            if progress_callback:
                progress_callback(100)
            if log_callback:
                log_callback("\n处理完成")
                log_callback(f"成功处理: {processed_files}/{total_files} 个文件")
                
        except Exception as e:
            if log_callback:
                log_callback(f"处理过程发生错误: {str(e)}")
            
        finally:
            self.processing = False
            self.pause_event.set()
            self.stop_event.clear()
    
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
