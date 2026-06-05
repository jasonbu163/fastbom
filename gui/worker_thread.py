# gui/worker_thread.py

import shutil
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from PySide6.QtCore import QThread, Signal

from config import AppSettings, load_settings
from core import BOMClassifier, DXFProcessor, SWConverter
from utils import logger
from utils.platform_capabilities import detect_platform_capabilities


class WorkerThread(QThread):
    """后台任务线程"""
    progress = Signal(int)
    log_message = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(
        self,
        task_type: str,
        classifier: BOMClassifier,
        config: Optional[Dict[str, str]] = None,
        app_settings: Optional[AppSettings] = None,
    ):
        super().__init__()
        self.task_type = task_type
        self.classifier = classifier
        self.config = config or {}
        self.app_settings = app_settings or load_settings()
    
    def run(self) -> None:
        try:
            if self.task_type == "classify_and_convert":
                self._run_classification_with_conversion()
            elif self.task_type == "process_dxf":
                self._run_dxf_processing()
            elif self.task_type == "merge_dxf":
                self._run_dxf_merge()
        except Exception as e:
            self.log_message.emit(f"执行出错: {str(e)}")
            self.finished.emit(False, str(e))
    
    def _run_classification_with_conversion(self) -> None:
        """文件分类 + DXF转换任务（整合）"""
        if not self.classifier.bom_file:
            self.finished.emit(False, "请先选择BOM表")
            return
        
        if not self.classifier.project_dir:
            self.finished.emit(False, "请先选择项目目录")
            return
        
        self.log_message.emit("开始执行分类和转换任务...")
        self.log_message.emit("=" * 60)
        
        # 读取BOM表
        df = pd.read_excel(self.classifier.bom_file, header=self.classifier.header_row).fillna('')
        df = df.dropna(how='all')
        
        # 构建SLDDRW文件索引
        slddrw_files = self.classifier.find_slddrw_files()
        slddrw_dict: Dict[str, Path] = {}
        for file in slddrw_files:
            # 使用文件名（不含扩展名）作为键，支持模糊匹配
            stem = file.stem.lower()
            slddrw_dict[stem] = file
        
        self.log_message.emit(f"找到 {len(slddrw_dict)} 个工程图文件")
        self.log_message.emit(f"BOM表包含 {len(df)} 行数据")
        self.log_message.emit("=" * 60)
        
        # ===== 第一阶段：预处理 - 筛选出需要处理的文件 =====
        self.log_message.emit("正在分析BOM表，筛选有效零件...")
        
        tasks_to_process = []  # 存储需要处理的任务
        skip_reasons = {
            'no_part_name': 0,
            'invalid_material': 0,
            'no_matched_file': 0
        }
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            part_name = str(row.get(self.config.get('part', ''), '')).strip()
            material_raw = str(row.get(self.config.get('mat', ''), '')).strip()
            quantity = str(row.get(self.config.get('qty', '1'), '1')).strip()
            
            # 检查零件名
            if not part_name or part_name == 'nan':
                skip_reasons['no_part_name'] += 1
                continue
            
            # 检查材料格式
            material, thickness = self.classifier.parse_material(material_raw)
            if not material or not thickness:
                skip_reasons['invalid_material'] += 1
                self.log_message.emit(f"跳过 - 材料格式不正确: {part_name} ({material_raw})")
                continue
            
            # 检查是否有匹配的文件
            matched_file = self._fuzzy_match_file(part_name, slddrw_dict)
            if not matched_file:
                skip_reasons['no_matched_file'] += 1
                self.log_message.emit(f"跳过 - 未找到工程图: {part_name}")
                continue
            
            # 添加到处理列表
            tasks_to_process.append({
                'part_name': part_name,
                'material': material,
                'thickness': thickness,
                'quantity': quantity,
                'matched_file': matched_file
            })
        
        # 统计信息
        total_to_process = len(tasks_to_process)
        total_skipped = sum(skip_reasons.values())
        
        self.log_message.emit("=" * 60)
        self.log_message.emit("预处理完成:")
        self.log_message.emit(f"   需要处理: {total_to_process} 个零件")
        self.log_message.emit(f"   已跳过: {total_skipped} 个零件")
        if skip_reasons['no_part_name'] > 0:
            self.log_message.emit(f"      - 无零件名: {skip_reasons['no_part_name']} 个")
        if skip_reasons['invalid_material'] > 0:
            self.log_message.emit(f"      - 材料格式错误: {skip_reasons['invalid_material']} 个")
        if skip_reasons['no_matched_file'] > 0:
            self.log_message.emit(f"      - 未找到工程图: {skip_reasons['no_matched_file']} 个")
        self.log_message.emit("=" * 60)
        
        if total_to_process == 0:
            self.finished.emit(False, "没有找到需要处理的文件")
            return
        
        # ===== 第二阶段：初始化SolidWorks并转换 =====
        capabilities = detect_platform_capabilities()
        if not capabilities.solidworks_local_processing_available:
            self.finished.emit(False, capabilities.solidworks_local_processing_reason)
            return

        self.log_message.emit("正在初始化 SolidWorks...")
        sw_converter = SWConverter(solidworks_config=self.app_settings.solidworks)
        if not sw_converter.initialize():
            self.finished.emit(False, "SolidWorks初始化失败")
            return
        
        try:
            success_count = 0
            fail_count = 0
            
            for idx, task in enumerate(tasks_to_process):
                part_name = task['part_name']
                material = task['material']
                thickness = task['thickness']
                quantity = task['quantity']
                matched_file = task['matched_file']
                
                # 准备输出目录
                dest_dir = self.classifier.classified_dir / material / thickness
                dest_dir.mkdir(parents=True, exist_ok=True)
                
                qty_prefix = quantity if quantity != 'nan' else '1'
                dxf_filename = f"({qty_prefix}){matched_file.stem}.dxf"
                dxf_output = dest_dir / dxf_filename
                
                # 转换为DXF
                current_progress = idx + 1
                self.log_message.emit(f"[{current_progress}/{total_to_process}] {part_name} → 正在转换...")
                success, msg = sw_converter.convert_to_dxf(matched_file, dxf_output)
                
                if success:
                    success_count += 1
                    self.log_message.emit(f"[{current_progress}/{total_to_process}] {part_name} → {material}/{thickness}/{dxf_filename}")
                else:
                    fail_count += 1
                    self.log_message.emit(f"[{current_progress}/{total_to_process}] {msg}")
                
                # 更新进度条（基于实际处理的文件数）
                self.progress.emit(int((current_progress / total_to_process) * 100))
            
            self.log_message.emit("=" * 60)
            self.log_message.emit("任务完成。")
            self.log_message.emit(f"   成功转换: {success_count} 个文件")
            if fail_count > 0:
                self.log_message.emit(f"   转换失败: {fail_count} 个文件")
            if total_skipped > 0:
                self.log_message.emit(f"   已跳过: {total_skipped} 个零件")
            self.log_message.emit(f"   总计处理: {success_count + fail_count}/{len(df)} (有效率: {(success_count + fail_count)/len(df)*100:.1f}%)")
            
            self.finished.emit(True, f"成功转换并归档 {success_count} 个文件")
            
        finally:
            # 关闭SolidWorks
            self.log_message.emit("正在关闭 SolidWorks...")
            sw_converter.shutdown()
    
    def _fuzzy_match_file(self, part_name: str, file_dict: Dict[str, Path]) -> Optional[Path]:
        """
        模糊匹配文件名
        
        Args:
            part_name: BOM中的零件名
            file_dict: 文件字典（键为小写文件名）
        
        Returns:
            匹配的文件路径，如果未找到返回None
        """
        part_name_lower = part_name.lower()
        
        # 1. 精确匹配
        if part_name_lower in file_dict:
            return file_dict[part_name_lower]
        
        # 2. 包含匹配
        for file_stem, file_path in file_dict.items():
            if part_name_lower in file_stem or file_stem in part_name_lower:
                return file_path
        
        return None
    
    def _run_dxf_processing(self) -> None:
        """DXF处理任务"""
        self.log_message.emit("开始处理DXF文件...")
        
        if self.classifier.processed_dxf_dir.exists():
            shutil.rmtree(self.classifier.processed_dxf_dir)
        self.classifier.processed_dxf_dir.mkdir(parents=True)
        
        dxf_files = list(self.classifier.classified_dir.rglob("*.dxf"))
        self.log_message.emit(f"找到 {len(dxf_files)} 个DXF文件")
        
        success_count = 0
        processor = DXFProcessor(dxf_config=self.app_settings.dxf)
        
        for idx, dxf_file in enumerate(dxf_files):
            import re
            match = re.search(r'\((\d+)\)', dxf_file.name)
            quantity = int(match.group(1)) if match else 1
            
            rel_path = dxf_file.parent.relative_to(self.classifier.classified_dir)
            output_dir = self.classifier.processed_dxf_dir / rel_path
            output_dir.mkdir(parents=True, exist_ok=True)
            
            success, msg = processor.process_dxf_file(dxf_file, quantity, output_dir)
            self.log_message.emit(msg)
            
            if success:
                success_count += 1
            
            self.progress.emit(int((idx + 1) / len(dxf_files) * 100))
        
        self.log_message.emit("=" * 60)
        self.log_message.emit(f"DXF处理完成。成功: {success_count}/{len(dxf_files)}")
        self.finished.emit(True, f"成功处理 {success_count} 个文件")
    
    def _run_dxf_merge(self) -> None:
        """DXF合并任务"""
        self.log_message.emit("开始按材料/厚度合并DXF文件...")
        self.log_message.emit("=" * 60)
        
        processor = DXFProcessor(dxf_config=self.app_settings.dxf)
        source_dir = self.classifier.classified_dir
        output_dir = self.classifier.merged_dir
        
        success_count, fail_count, logs = processor.merge_by_thickness(source_dir, output_dir)
        
        for log in logs:
            self.log_message.emit(log)
        
        self.log_message.emit("=" * 60)
        self.log_message.emit(f"合并完成。成功: {success_count} 组, 失败: {fail_count} 组")
        
        if success_count > 0:
            self.finished.emit(True, f"成功合并 {success_count} 组文件")
        else:
            self.finished.emit(False, "没有成功合并任何文件")
