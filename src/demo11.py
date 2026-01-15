# fastbom

import os
import re
import sys
import shutil
import platform
from pathlib import Path
from typing import Optional, Tuple, List, Dict
import pandas as pd
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QGroupBox, QMessageBox,
    QGridLayout, QScrollArea, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon

from ezdxf import zoom, addons
from ezdxf.filemanagement import readfile, new
from ezdxf.bbox import extents
from ezdxf.document import Drawing
from ezdxf.layouts import Modelspace


class DXFProcessor:
    """DXF文件处理器"""
    
    # 统一的文本配置
    TEXT_HEIGHT = 50  # 统一的文本高度
    TEXT_LAYER = "0"  # 文本插入的图层
    TEXT_COLOR = 2  # 黄色
    
    @staticmethod
    def process_dxf_file(file_path: Path, num: int, output_dir: Path) -> Tuple[bool, str]:
        """处理DXF文件：在图层0实体上方添加文件名标注
        
        Args:
            file_path: DXF文件路径
            num: 数量（暂未使用）
            output_dir: 输出目录
        
        Returns:
            (成功标志, 消息)
        """
        try:
            doc: Drawing = readfile(str(file_path))
            msp = doc.modelspace()
            
            if '0' not in doc.layers:
                return False, f"❌ 文件中不存在图层0: {file_path.name}"
            
            # 获取图层0实体
            layer_0_entities = [e for e in msp if hasattr(e.dxf, 'layer') and e.dxf.layer == '0']
            if not layer_0_entities:
                return False, f"❌ 图层0中没有实体: {file_path.name}"
            
            # 插入文件名标注
            try:
                entity_extent = extents(layer_0_entities)
                if entity_extent.has_data:
                    # 在图层0实体的左上角添加文本
                    text_height = max((entity_extent.extmax.y - entity_extent.extmin.y) * 0.1, 5.0)
                    insert_pos = (0, - text_height * 1.5)
                else:
                    text_height = 10
                    insert_pos = (0, 0)

                file_name_to_insert = file_path.stem
                msp.add_text(
                    file_name_to_insert,
                    dxfattribs={
                        'layer': DXFProcessor.TEXT_LAYER,
                        'height': text_height,
                        'color': DXFProcessor.TEXT_COLOR
                    }
                ).set_placement(insert_pos)
            except Exception as text_err:
                print(f"插入文字提示: {text_err}")
            
            # 保存文件
            zoom.extents(msp)
            output_file = output_dir / f"processed_{file_path.name}"
            doc.saveas(str(output_file))
            
            return True, f"✅ 成功处理 | 保存至: {output_file.name}"
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            print(f"详细错误信息:\n{error_detail}")
            return False, f"❌ 处理失败 [{file_path.name}]: {str(e)}"

    @staticmethod
    def merge_directory_to_dxf(input_dir: Path, output_file: Path) -> Tuple[bool, str]:
        """合并目录下所有DXF文件到一个文件
        
        Args:
            input_dir: 输入目录
            output_file: 输出文件路径
        
        Returns:
            (成功标志, 消息)
        """
        if not input_dir.is_dir():
            return False, f"❌ 错误: {input_dir} 不是有效的目录"

        # 创建新的目标 DXF 文件
        merged_doc: Drawing = new()
        merged_msp = merged_doc.modelspace()
        
        # 获取目录下所有 dxf 文件（递归）
        dxf_files = sorted(list(input_dir.rglob("*.dxf")))
        if not dxf_files:
            return False, "⚠️ 文件夹内没有 DXF 文件"

        current_x_offset = 0.0
        spacing = 100.0  # 每个模型之间的间距
        success_count = 0

        for dxf_file in dxf_files:
            try:
                # 读取源文件
                source_doc: Drawing = readfile(str(dxf_file))
                source_msp = source_doc.modelspace()
                
                # 获取所有实体
                entities = list(source_msp.query('*'))
                if not entities:
                    continue
                
                # 计算源文件的包围盒
                bbox = extents(entities)
                if not bbox.has_data:
                    continue

                # 创建唯一的块名（避免重名）
                block_name = f"block_{dxf_file.stem}_{success_count}".replace(" ", "_")[:100]
                
                # 创建新块并导入实体
                new_block = merged_doc.blocks.new(name=block_name)
                importer = addons.importer.Importer(source_doc, merged_doc)
                importer.import_entities(entities, target_layout=new_block)
                importer.finalize()

                # 插入块到指定位置（保持底部对齐）
                insert_point = (current_x_offset, 0, 0)
                merged_msp.add_blockref(block_name, insert_point)
                
                # 添加文件名标注 - 使用统一的文本高度
                file_label = dxf_file.stem
                model_height = bbox.extmax.y - bbox.extmin.y
                # 文本放在模型下方
                text_y = model_height + DXFProcessor.TEXT_HEIGHT
                # 文本在x轴下方
                # text_y = - DXFProcessor.TEXT_HEIGHT * 1.5
                merged_msp.add_text(
                    file_label,
                    dxfattribs={
                        'height': DXFProcessor.TEXT_HEIGHT,  # 统一高度
                        'layer': DXFProcessor.TEXT_LAYER,
                        'color': DXFProcessor.TEXT_COLOR
                    }
                ).set_placement((current_x_offset, text_y))

                # 更新下一个模型的 X 轴偏移量
                model_width = bbox.extmax.x - bbox.extmin.x
                current_x_offset += model_width + spacing

                success_count += 1

            except Exception as e:
                print(f"❌ 处理 {dxf_file.name} 失败: {e}")

        if success_count == 0:
            return False, "❌ 没有成功合并任何文件"
        
        # 隐藏其他图层（保留0层和细实线层）
        visible_layers = {'0', '细实线层'}
        for layer in merged_doc.layers:
            if layer.dxf.name not in visible_layers:
                layer.off()

        # 保存最终文件
        try:
            zoom.extents(merged_msp)
            merged_doc.saveas(str(output_file))
            return True, f"✅ 成功合并 {success_count} 个文件到: {output_file.name}"
        except Exception as e:
            return False, f"❌ 保存合并文件失败: {str(e)}"

    @staticmethod
    def merge_by_thickness(source_dir: Path, output_dir: Path) -> Tuple[int, int, List[str]]:
        """遍历分类后的文件夹结构（材料/厚度），并对每个底层文件夹执行合并
        
        Args:
            source_dir: 源目录（分类结果目录）
            output_dir: 输出目录
        
        Returns:
            (成功组数, 失败组数, 日志列表)
        """
        success_count = 0
        fail_count = 0
        logs: List[str] = []

        if not source_dir.exists():
            return 0, 0, ["❌ 源目录不存在"]

        # 遍历材料层 (例如: 铝板, 不锈钢板)
        for material_dir in sorted(source_dir.iterdir()):
            if not material_dir.is_dir():
                continue
            
            # 遍历厚度层 (例如: 2.0, 3.0)
            for thickness_dir in sorted(material_dir.iterdir()):
                if not thickness_dir.is_dir():
                    continue
                
                logs.append(f"📦 正在合并组: {material_dir.name} - {thickness_dir.name}")
                
                # 生成输出文件名: 材料_厚度_merged.dxf
                output_filename = f"{material_dir.name}_{thickness_dir.name}_merged.dxf"
                target_file = output_dir / output_filename
                
                # 调用现有的合并单个目录的方法
                success, msg = DXFProcessor.merge_directory_to_dxf(thickness_dir, target_file)
                
                if success:
                    success_count += 1
                    logs.append(f"  {msg}")
                else:
                    fail_count += 1
                    logs.append(f"  {msg}")
        
        return success_count, fail_count, logs


class WorkerThread(QThread):
    """后台任务线程"""
    progress = Signal(int)
    log_message = Signal(str)
    finished = Signal(bool, str)
    
    def __init__(self, task_type: str, classifier: 'BOMClassifier', config: Optional[Dict[str, str]] = None):
        super().__init__()
        self.task_type = task_type
        self.classifier = classifier
        self.config = config or {}
    
    def run(self) -> None:
        try:
            if self.task_type == "classify":
                self._run_classification()
            elif self.task_type == "process_dxf":
                self._run_dxf_processing()
            elif self.task_type == "merge_dxf":
                self._run_dxf_merge()
        except Exception as e:
            self.log_message.emit(f"💥 执行出错: {str(e)}")
            self.finished.emit(False, str(e))
    
    def _run_classification(self) -> None:
        """文件分类任务"""
        if not self.classifier.bom_file:
            self.finished.emit(False, "请先选择BOM表")
            return
        
        if not self.classifier.source_dir:
            self.finished.emit(False, "请先选择源文件目录")
            return
        
        self.log_message.emit("🚀 开始执行分类任务...")
        
        df = pd.read_excel(self.classifier.bom_file, header=self.classifier.header_row).fillna('')
        df = df.dropna(how='all')
        
        # 构建源文件字典
        source_files_dict: Dict[str, List[Path]] = {}
        for file in self.classifier.source_dir.rglob('*'):
            if file.is_file():
                stem = file.stem
                if stem not in source_files_dict:
                    source_files_dict[stem] = []
                source_files_dict[stem].append(file)
        
        self.log_message.emit(f"📁 源文件组数量: {len(source_files_dict)}")
        
        success_count = 0
        file_copy_count = 0
        total_rows = len(df)
        
        for idx in range(total_rows):
            row = df.iloc[idx]
            part_name = str(row.get(self.config.get('part', ''), '')).strip()
            material_raw = str(row.get(self.config.get('mat', ''), '')).strip()
            quantity = str(row.get(self.config.get('qty', '1'), '1')).strip()
            
            if not part_name or part_name == 'nan':
                continue
            
            material, thickness = self.classifier.parse_material(material_raw)
            if not material or not thickness:
                continue
            
            # 查找匹配的文件
            found_files: List[Path] = []
            for file_stem, file_list in source_files_dict.items():
                if part_name in file_stem or file_stem in part_name:
                    found_files.extend(file_list)
                    break
            
            if found_files:
                try:
                    dest_dir = self.classifier.classified_dir / material / thickness
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    
                    qty_prefix = quantity if quantity != 'nan' else '1'
                    
                    for found_file in found_files:
                        new_name = f"({qty_prefix}){found_file.name}"
                        dest_file = dest_dir / new_name
                        shutil.copy2(found_file, dest_file)
                        file_copy_count += 1
                    
                    success_count += 1
                    self.log_message.emit(f"✅ [{success_count}] {part_name} → {material}/{thickness}/")
                except Exception as e:
                    self.log_message.emit(f"❌ {part_name} - 复制失败: {str(e)}")
            
            self.progress.emit(int((idx + 1) / total_rows * 100))
        
        self.log_message.emit("=" * 60)
        self.log_message.emit(f"🎉 分类完成！归档 {success_count} 组 {file_copy_count} 个文件")
        self.finished.emit(True, f"成功归档 {success_count} 组文件")
    
    def _run_dxf_processing(self) -> None:
        """DXF处理任务"""
        self.log_message.emit("🎨 开始处理DXF文件...")
        
        if self.classifier.processed_dxf_dir.exists():
            shutil.rmtree(self.classifier.processed_dxf_dir)
        self.classifier.processed_dxf_dir.mkdir(parents=True)
        
        dxf_files = list(self.classifier.classified_dir.rglob("*.dxf"))
        self.log_message.emit(f"📐 找到 {len(dxf_files)} 个DXF文件")
        
        success_count = 0
        processor = DXFProcessor()
        
        for idx, dxf_file in enumerate(dxf_files):
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
        self.log_message.emit(f"🎉 DXF处理完成！成功: {success_count}/{len(dxf_files)}")
        self.finished.emit(True, f"成功处理 {success_count} 个文件")
    
    def _run_dxf_merge(self) -> None:
        """DXF合并任务 - 按材料/厚度分组合并"""
        self.log_message.emit("🔗 开始按材料/厚度合并DXF文件...")
        self.log_message.emit("=" * 60)
        
        processor = DXFProcessor()
        
        # 从分类结果目录读取，输出到合并目录
        source_dir = self.classifier.classified_dir  # 1_分类结果
        output_dir = self.classifier.merged_dir  # 3_合并文件
        
        success_count, fail_count, logs = processor.merge_by_thickness(source_dir, output_dir)
        
        # 输出所有日志
        for log in logs:
            self.log_message.emit(log)
        
        self.log_message.emit("=" * 60)
        self.log_message.emit(f"🎉 合并完成！成功: {success_count} 组, 失败: {fail_count} 组")
        
        if success_count > 0:
            self.finished.emit(True, f"成功合并 {success_count} 组文件")
        else:
            self.finished.emit(False, "没有成功合并任何文件")


class BOMClassifier:
    """BOM分类器"""
    
    def __init__(self):
        self.bom_file: Optional[Path] = None
        self.source_dir: Optional[Path] = None
        self.result_dir: Optional[Path] = None
        self.classified_dir: Optional[Path] = None
        self.processed_dxf_dir: Optional[Path] = None
        self.merged_dir: Optional[Path] = None
        
        self.df: Optional[pd.DataFrame] = None
        self.headers: List[str] = []
        self.header_row: int = 0
    
    def set_bom_file(self, file_path: str) -> bool:
        """设置BOM文件"""
        self.bom_file = Path(file_path)
        return self.bom_file.exists()
    
    def set_source_dir(self, dir_path: str) -> bool:
        """设置源文件目录并创建result子目录"""
        self.source_dir = Path(dir_path)
        if self.source_dir.exists():
            # 在源文件目录下创建result目录
            self.result_dir = self.source_dir / "result"
            self.classified_dir = self.result_dir / "1_分类结果"
            self.processed_dxf_dir = self.result_dir / "2_DXF处理结果"
            self.merged_dir = self.result_dir / "3_合并文件"
            
            # 创建所有目录
            for directory in [self.result_dir, self.classified_dir, self.processed_dxf_dir, self.merged_dir]:
                directory.mkdir(exist_ok=True)
            
            return True
        return False
    
    def open_folder(self, path: Path) -> None:
        """跨平台打开文件夹"""
        import subprocess
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(str(path))
            elif system == 'Darwin':
                subprocess.run(['open', str(path)])
            else:
                subprocess.run(['xdg-open', str(path)])
        except Exception as e:
            print(f"无法打开文件夹: {e}")
    
    def detect_header_row(self, file_path: Path, max_rows: int = 20) -> Tuple[int, List[str]]:
        """智能检测表头所在行"""
        df_preview = pd.read_excel(file_path, header=None, nrows=max_rows)
        best_row = 0
        best_score = 0
        
        for i in range(min(max_rows, len(df_preview))):
            row = df_preview.iloc[i]
            score = 0
            valid_cols: List[str] = []
            
            for val in row:
                if pd.notna(val) and str(val).strip():
                    val_str = str(val).strip()
                    if not val_str.replace('.', '').replace('-', '').isdigit():
                        score += 1
                        valid_cols.append(val_str)
                    
                    keywords = ['名称', '材料', '材质', '厚度', '数量', '零件', '图号']
                    if any(kw in val_str.lower() for kw in keywords):
                        score += 5
            
            if score > best_score and len(valid_cols) >= 3:
                best_score = score
                best_row = i
        
        df = pd.read_excel(file_path, header=best_row, nrows=1)
        headers = [str(h) for h in df.columns if not str(h).startswith('Unnamed')]
        return best_row, headers
    
    def load_bom_headers(self) -> Tuple[bool, str]:
        """读取BOM并智能检测表头"""
        if not self.bom_file:
            return False, "请先选择BOM文件"
        
        try:
            self.header_row, self.headers = self.detect_header_row(self.bom_file)
            
            if not self.headers:
                return False, "未能识别有效表头"
            
            return True, f"成功加载: {self.bom_file.name} (表头在第 {self.header_row + 1} 行)"
        except Exception as e:
            return False, f"读取失败: {e}"
    
    def parse_material(self, material_str: str) -> Tuple[Optional[str], Optional[str]]:
        """解析材料字符串
        
        Args:
            material_str: 材料字符串，格式如 "铝板 T=2.0"
        
        Returns:
            (材料名称, 厚度) 或 (None, None)
        """
        if not material_str or pd.isna(material_str):
            return None, None
        
        material_str = str(material_str).strip()
        pattern = r'(.+?板)\s*T=(\d+(?:\.\d+)?)'
        match = re.search(pattern, material_str)
        if match:
            return match.group(1).strip(), match.group(2).strip()
        return None, None


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.classifier = BOMClassifier()
        self.config: Dict[str, str] = {'part': '图号', 'mat': '材料', 'qty': '总数量'}
        self.worker: Optional[WorkerThread] = None
        
        self.setWindowTitle("BOM智能分类助手 + DXF处理器")
        self.setMinimumSize(800, 600)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # 标题
        # self._create_header(scroll_layout)
        
        # 步骤1：选择文件和目录
        self._create_step1(scroll_layout)
        
        # 步骤2：表头识别
        self._create_step2(scroll_layout)
        
        # 步骤3：文件分类
        self._create_step3(scroll_layout)
        
        # 步骤4：DXF处理
        self._create_step4(scroll_layout)
        
        # 步骤5：DXF合并
        self._create_step5(scroll_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def _create_header(self, layout: QVBoxLayout) -> None:
        """创建标题区域"""
        header_group = QGroupBox()
        header_layout = QVBoxLayout()
        
        title = QLabel("BOM智能分类助手 + DXF处理器")
        title.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitle = QLabel("自动分类 · 智能处理DXF · 一站式工程文件管理")
        subtitle.setFont(QFont("Arial", 12))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        header_group.setLayout(header_layout)
        layout.addWidget(header_group)
    
    def _create_step1(self, layout: QVBoxLayout) -> None:
        """步骤1：选择文件和目录"""
        group = QGroupBox("第一步：选择BOM表和源文件目录")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        # BOM文件选择
        bom_layout = QHBoxLayout()
        bom_layout.addWidget(QLabel("BOM表:"))
        self.bom_path_edit = QLineEdit()
        self.bom_path_edit.setReadOnly(True)
        self.bom_path_edit.setPlaceholderText("请选择BOM Excel文件...")
        bom_layout.addWidget(self.bom_path_edit)
        
        bom_btn = QPushButton("📄 选择BOM表")
        bom_btn.setMaximumWidth(150)
        bom_btn.clicked.connect(self._select_bom_file)
        bom_layout.addWidget(bom_btn)
        
        # 源文件目录选择
        src_layout = QHBoxLayout()
        src_layout.addWidget(QLabel("源文件:"))
        self.source_path_edit = QLineEdit()
        self.source_path_edit.setReadOnly(True)
        self.source_path_edit.setPlaceholderText("请选择源文件所在目录...")
        src_layout.addWidget(self.source_path_edit)
        
        src_btn = QPushButton("📁 选择源目录")
        src_btn.setMaximumWidth(150)
        src_btn.clicked.connect(self._select_source_dir)
        src_layout.addWidget(src_btn)
        
        # 说明文字
        info = QLabel("💡 处理结果将保存在源文件目录下的 'result' 文件夹中")
        
        group_layout.addLayout(bom_layout)
        group_layout.addLayout(src_layout)
        group_layout.addWidget(info)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step2(self, layout: QVBoxLayout) -> None:
        """步骤2：表头识别"""
        group = QGroupBox("第二步：智能识别表头")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        self.header_label = QLabel("等待选择BOM表...")
        self.header_label.setFont(QFont("Arial", 11))
        
        grid = QGridLayout()
        grid.addWidget(QLabel(f"📋 零件号列: {self.config['part']}"), 0, 0)
        grid.addWidget(QLabel(f"🔧 材质列: {self.config['mat']}"), 0, 1)
        grid.addWidget(QLabel(f"🔢 数量列: {self.config['qty']}"), 0, 2)
        
        group_layout.addWidget(self.header_label)
        group_layout.addLayout(grid)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step3(self, layout: QVBoxLayout) -> None:
        """步骤3：文件分类"""
        group = QGroupBox("第三步：文件分类归档")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        btn = QPushButton("🚀 开始文件分类")
        # btn.setMinimumHeight(60)
        btn.clicked.connect(self._on_classify)
        
        self.progress1 = QProgressBar()
        # self.progress1.setMinimumHeight(30)
        
        self.log1 = QTextEdit()
        self.log1.setReadOnly(True)
        # self.log1.setMinimumHeight(200)
        
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress1)
        group_layout.addWidget(self.log1)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step4(self, layout: QVBoxLayout) -> None:
        """步骤4：DXF处理"""
        group = QGroupBox("第四步：DXF智能处理")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        info = QLabel("功能：在细实线层（纸张边框）下方添加文件名标注")
        
        btn = QPushButton("🎨 开始处理DXF文件")
        # btn.setMinimumHeight(60)
        btn.clicked.connect(self._on_process_dxf)
        
        self.progress2 = QProgressBar()
        # self.progress2.setMinimumHeight(30)
        
        self.log2 = QTextEdit()
        self.log2.setReadOnly(True)
        # self.log2.setMinimumHeight(200)
        
        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress2)
        group_layout.addWidget(self.log2)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step5(self, layout: QVBoxLayout) -> None:
        """步骤5：DXF合并"""
        group = QGroupBox("第五步：按材料/厚度合并DXF文件")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        info = QLabel("功能：将同一材料和厚度的DXF文件合并到一个文件，在细实线层下方添加统一标注")
        
        btn = QPushButton("🔗 开始合并DXF文件")
        # btn.setMinimumHeight(60)
        btn.clicked.connect(self._on_merge_dxf)
        
        self.progress3 = QProgressBar()
        # self.progress3.setMinimumHeight(30)
        
        self.log3 = QTextEdit()
        self.log3.setReadOnly(True)
        # self.log3.setMinimumHeight(200)
        
        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress3)
        group_layout.addWidget(self.log3)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _select_bom_file(self) -> None:
        """选择BOM文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择BOM表",
            "",
            "Excel Files (*.xlsx *.xls)"
        )
        
        if file_path:
            if self.classifier.set_bom_file(file_path):
                self.bom_path_edit.setText(file_path)
                QMessageBox.information(self, "成功", "✅ BOM表已加载")
                # 自动加载表头
                self._load_headers()
            else:
                QMessageBox.warning(self, "错误", "❌ 无效的文件路径")
    
    def _select_source_dir(self) -> None:
        """选择源文件目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择源文件目录",
            ""
        )
        
        if dir_path:
            if self.classifier.set_source_dir(dir_path):
                self.source_path_edit.setText(dir_path)
                result_dir_str = str(self.classifier.result_dir) if self.classifier.result_dir else ""
                QMessageBox.information(
                    self, 
                    "成功", 
                    f"✅ 源文件目录已设置\n结果将保存在:\n{result_dir_str}"
                )
            else:
                QMessageBox.warning(self, "错误", "❌ 无效的目录路径")
    
    def _load_headers(self) -> None:
        """加载BOM表头"""
        success, msg = self.classifier.load_bom_headers()
        self.header_label.setText(msg)
        if success:
            self.header_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.header_label.setStyleSheet("color: orange;")
    
    def _on_classify(self) -> None:
        """启动分类任务"""
        if not self.classifier.bom_file:
            QMessageBox.warning(self, "提示", "⚠️ 请先选择BOM表")
            return
        
        if not self.classifier.source_dir:
            QMessageBox.warning(self, "提示", "⚠️ 请先选择源文件目录")
            return
        
        self.log1.clear()
        self.progress1.setValue(0)
        
        self.worker = WorkerThread("classify", self.classifier, self.config)
        self.worker.progress.connect(self.progress1.setValue)
        self.worker.log_message.connect(lambda msg: self.log1.append(msg))
        self.worker.finished.connect(self._on_classify_finished)
        self.worker.start()
    
    def _on_classify_finished(self, success: bool, msg: str) -> None:
        """分类完成"""
        if success and self.classifier.classified_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.classified_dir)
        else:
            QMessageBox.warning(self, "失败", msg)
    
    def _on_process_dxf(self) -> None:
        """启动DXF处理任务"""
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "⚠️ 请先完成文件分类")
            return
        
        self.log2.clear()
        self.progress2.setValue(0)
        
        self.worker = WorkerThread("process_dxf", self.classifier, self.config)
        self.worker.progress.connect(self.progress2.setValue)
        self.worker.log_message.connect(lambda msg: self.log2.append(msg))
        self.worker.finished.connect(self._on_process_dxf_finished)
        self.worker.start()
    
    def _on_process_dxf_finished(self, success: bool, msg: str) -> None:
        """DXF处理完成"""
        if success and self.classifier.processed_dxf_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.processed_dxf_dir)
        else:
            QMessageBox.warning(self, "失败", msg)
    
    def _on_merge_dxf(self) -> None:
        """启动DXF合并任务"""
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "⚠️ 请先完成文件分类")
            return
        
        self.log3.clear()
        self.progress3.setValue(0)
        
        self.worker = WorkerThread("merge_dxf", self.classifier)
        self.worker.log_message.connect(lambda msg: self.log3.append(msg))
        self.worker.finished.connect(self._on_merge_dxf_finished)
        self.worker.start()
    
    def _on_merge_dxf_finished(self, success: bool, msg: str) -> None:
        """DXF合并完成"""
        self.progress3.setValue(100)
        if success and self.classifier.merged_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.merged_dir)
        else:
            QMessageBox.warning(self, "失败", msg)


def main() -> None:
    """主函数"""
    from qt_material import apply_stylesheet

    app = QApplication(sys.argv)
    
    # 应用qt-material主题
    apply_stylesheet(app, theme="dark_teal.xml")

    # 设置本地图标
    icon = QIcon("static/efficacy_researching_settings_icon_152066.ico")
    
    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()