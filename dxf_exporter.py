"""
DXF/DWG 导出扩展 - 扩展混合处理器
支持多种导出场景：图纸、钣金展开图、草图等
"""
import win32com.client
import pythoncom
from pathlib import Path
from typing import List, Optional, Tuple, Dict
from enum import Enum
from dataclasses import dataclass


class ExportFormat(Enum):
    """导出格式"""
    DXF = ".dxf"
    DWG = ".dwg"


class DXFExportType(Enum):
    """DXF 导出类型"""
    DRAWING = "drawing"           # 图纸导出
    SHEET_METAL = "sheet_metal"   # 钣金展开图
    SKETCH = "sketch"             # 草图导出
    FLAT_PATTERN = "flat_pattern" # 展开视图


@dataclass
class DXFExportOptions:
    """DXF 导出选项"""
    include_bend_lines: bool = True         # 包含折弯线
    include_sketches: bool = False          # 包含草图
    include_annotations: bool = True        # 包含注释
    export_hidden_entities: bool = False    # 导出隐藏实体
    map_fonts: bool = True                  # 映射字体
    
    # 钣金特定选项
    sheet_metal_options: int = 13  # 二进制: 0001101
    # Bit 0 (1) = Include Flat Pattern Geometry
    # Bit 2 (4) = Include Bend Lines  
    # Bit 3 (8) = Include Sketches


class DXFExporter:
    """
    DXF/DWG 导出器
    
    支持的导出场景：
    1. 图纸整体导出
    2. 图纸指定图页导出
    3. 钣金零件展开图导出
    4. 草图导出
    """
    
    def __init__(self, sw_app):
        """
        初始化导出器
        
        Args:
            sw_app: SolidWorks Application 对象
        """
        self.sw_app = sw_app
    
    # ==================== 图纸导出 ====================
    
    def export_drawing(
        self,
        drawing_path: str,
        output_path: str,
        export_format: ExportFormat = ExportFormat.DXF,
        sheets: Optional[List[str]] = None,
        options: Optional[DXFExportOptions] = None
    ) -> bool:
        """
        导出图纸为 DXF/DWG
        
        Args:
            drawing_path: 图纸文件路径
            output_path: 输出路径
            export_format: 导出格式
            sheets: 要导出的图页名称列表（None = 全部）
            options: 导出选项
            
        Returns:
            是否成功
        """
        if options is None:
            options = DXFExportOptions()
        
        try:
            # 打开图纸
            doc = self._open_document(drawing_path, 3)  # 3 = Drawing
            if not doc:
                return False
            
            # 设置导出选项
            self._configure_export_options(options)
            
            # 执行导出
            errors = 0
            warnings = 0
            
            # 如果指定了特定图页
            if sheets:
                success = self._export_specific_sheets(doc, output_path, sheets, export_format)
            else:
                # 导出所有图页
                success = doc.SaveAs4(
                    output_path,
                    0,  # swSaveAsCurrentVersion
                    0,  # swSaveAsOptions_Silent
                    errors,
                    warnings
                )
            
            # 关闭文档
            self.sw_app.CloseDoc(drawing_path)
            
            return success and errors == 0
            
        except Exception as e:
            print(f"导出图纸失败: {e}")
            return False
    
    def batch_export_drawings(
        self,
        drawing_paths: List[str],
        output_dir: str,
        export_format: ExportFormat = ExportFormat.DXF,
        options: Optional[DXFExportOptions] = None,
        progress_callback=None
    ) -> List[Dict]:
        """
        批量导出图纸
        
        Args:
            drawing_paths: 图纸路径列表
            output_dir: 输出目录
            export_format: 导出格式
            options: 导出选项
            progress_callback: 进度回调
            
        Returns:
            结果列表
        """
        results = []
        total = len(drawing_paths)
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        for idx, drawing_path in enumerate(drawing_paths):
            if progress_callback:
                progress_callback(idx + 1, total, drawing_path)
            
            # 生成输出路径
            filename = Path(drawing_path).stem
            output_path = output_dir_path / f"{filename}{export_format.value}"
            
            # 导出
            success = self.export_drawing(
                drawing_path,
                str(output_path),
                export_format,
                options=options
            )
            
            results.append({
                "input": drawing_path,
                "output": str(output_path),
                "success": success
            })
        
        return results
    
    # ==================== 钣金展开图导出 ====================
    
    def export_sheet_metal_flat_pattern(
        self,
        part_path: str,
        output_path: str,
        export_format: ExportFormat = ExportFormat.DXF,
        options: Optional[DXFExportOptions] = None
    ) -> bool:
        """
        导出钣金零件的展开图
        
        Args:
            part_path: 钣金零件路径
            output_path: 输出路径
            export_format: 导出格式
            options: 导出选项
            
        Returns:
            是否成功
        """
        if options is None:
            options = DXFExportOptions()
        
        try:
            # 打开零件
            doc = self._open_document(part_path, 1)  # 1 = Part
            if not doc:
                return False
            
            # 获取零件文档接口
            part = doc
            
            # 确保是钣金零件
            if not part.IsSheetMetal():
                print("警告：不是钣金零件")
                return False
            
            # 导出为 DXF/DWG
            success = part.ExportToDWG2(
                output_path,
                part_path,
                1,  # swExportToDWG_ExportSheetMetal
                True,  # bCurrentSheetMetalState
                None,  # ExportData
                False,  # bUseGRFilter
                False,  # bViewsOnly
                options.sheet_metal_options,  # SheetMetalOptions
                None   # pSheets
            )
            
            # 关闭文档
            self.sw_app.CloseDoc(part_path)
            
            return success
            
        except Exception as e:
            print(f"导出钣金展开图失败: {e}")
            return False
    
    def batch_export_sheet_metal(
        self,
        part_paths: List[str],
        output_dir: str,
        export_format: ExportFormat = ExportFormat.DXF,
        options: Optional[DXFExportOptions] = None,
        progress_callback=None
    ) -> List[Dict]:
        """
        批量导出钣金展开图
        
        Args:
            part_paths: 零件路径列表
            output_dir: 输出目录
            export_format: 导出格式
            options: 导出选项
            progress_callback: 进度回调
            
        Returns:
            结果列表
        """
        results = []
        total = len(part_paths)
        output_dir_path = Path(output_dir)
        output_dir_path.mkdir(parents=True, exist_ok=True)
        
        for idx, part_path in enumerate(part_paths):
            if progress_callback:
                progress_callback(idx + 1, total, part_path)
            
            # 生成输出路径
            filename = Path(part_path).stem
            output_path = output_dir_path / f"{filename}_flat{export_format.value}"
            
            # 导出
            success = self.export_sheet_metal_flat_pattern(
                part_path,
                str(output_path),
                export_format,
                options=options
            )
            
            results.append({
                "input": part_path,
                "output": str(output_path),
                "success": success,
                "type": "sheet_metal"
            })
        
        return results
    
    # ==================== 草图导出 ====================
    
    def export_sketch_to_dxf(
        self,
        model_path: str,
        sketch_name: str,
        output_path: str,
        export_format: ExportFormat = ExportFormat.DXF
    ) -> bool:
        """
        导出指定草图为 DXF/DWG
        
        Args:
            model_path: 模型路径（零件或装配体）
            sketch_name: 草图名称
            output_path: 输出路径
            export_format: 导出格式
            
        Returns:
            是否成功
        """
        try:
            # 确定文档类型
            ext = Path(model_path).suffix.lower()
            doc_type = 1 if ext == '.sldprt' else 2  # 1=Part, 2=Assembly
            
            # 打开文档
            doc = self._open_document(model_path, doc_type)
            if not doc:
                return False
            
            # 选择草图
            sketch_feat = doc.FeatureByName(sketch_name)
            if not sketch_feat:
                print(f"未找到草图: {sketch_name}")
                return False
            
            # 检查是否是草图
            if sketch_feat.GetTypeName2() != "ProfileFeature":
                print(f"{sketch_name} 不是草图特征")
                return False
            
            # 选择并复制草图
            sketch_feat.Select2(False, -1)
            doc.EditCopy()
            
            # 创建临时图纸
            draw_template = self.sw_app.GetUserPreferenceStringValue(56)  # swDefaultTemplateDrawing
            if not draw_template:
                print("未设置默认图纸模板")
                return False
            
            temp_draw = self.sw_app.NewDocument(
                draw_template,
                12,  # swDwgPapersUserDefined
                0.1,
                0.1
            )
            
            # 粘贴草图
            temp_draw.Paste()
            
            # 保存为 DXF/DWG
            errors = 0
            warnings = 0
            success = temp_draw.SaveAs4(
                output_path,
                0,  # swSaveAsCurrentVersion
                0,  # swSaveAsOptions_Silent
                errors,
                warnings
            )
            
            # 关闭文档
            self.sw_app.CloseDoc(temp_draw.GetPathName())
            self.sw_app.CloseDoc(model_path)
            
            return success and errors == 0
            
        except Exception as e:
            print(f"导出草图失败: {e}")
            return False
    
    # ==================== 工具方法 ====================
    
    def _open_document(self, path: str, doc_type: int):
        """
        打开文档
        
        Args:
            path: 文件路径
            doc_type: 文档类型 (1=Part, 2=Assembly, 3=Drawing)
            
        Returns:
            文档对象
        """
        errors = 0
        warnings = 0
        doc = self.sw_app.OpenDoc6(
            str(path),
            doc_type,
            0,  # Options
            "",  # Configuration
            errors,
            warnings
        )
        return doc
    
    def _configure_export_options(self, options: DXFExportOptions):
        """配置导出选项"""
        # 设置系统选项
        # 这些设置会影响后续的导出操作
        
        # 映射字体
        if options.map_fonts:
            self.sw_app.SetUserPreferenceToggle(122, True)  # swDxfMappingFiles
        
        # 其他选项可以根据需要添加
        pass
    
    def _export_specific_sheets(
        self,
        doc,
        output_path: str,
        sheets: List[str],
        export_format: ExportFormat
    ) -> bool:
        """导出指定的图页"""
        # 获取所有图页
        sheet_names = doc.GetSheetNames()
        
        # 激活并导出每个指定的图页
        for sheet_name in sheets:
            if sheet_name in sheet_names:
                doc.ActivateSheet(sheet_name)
                
                # 生成输出文件名
                base_name = Path(output_path).stem
                output_dir = Path(output_path).parent
                sheet_output = output_dir / f"{base_name}_{sheet_name}{export_format.value}"
                
                errors = 0
                warnings = 0
                success = doc.SaveAs4(
                    str(sheet_output),
                    0,
                    0,
                    errors,
                    warnings
                )
                
                if not success or errors != 0:
                    return False
        
        return True
    
    def get_export_info(self, file_path: str) -> Dict:
        """
        获取文件的导出信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            信息字典
        """
        info = {
            "file_path": file_path,
            "file_type": None,
            "exportable": False,
            "export_types": []
        }
        
        ext = Path(file_path).suffix.lower()
        
        if ext == '.slddrw':
            info["file_type"] = "Drawing"
            info["exportable"] = True
            info["export_types"] = ["DXF", "DWG", "PDF"]
        elif ext == '.sldprt':
            info["file_type"] = "Part"
            info["exportable"] = True
            info["export_types"] = ["DXF (Sketch)", "DXF (Sheet Metal)"]
        elif ext == '.sldasm':
            info["file_type"] = "Assembly"
            info["exportable"] = True
            info["export_types"] = ["DXF (Sketch)"]
        
        return info


# ==================== 集成到混合处理器 ====================

class EnhancedSolidWorksProcessor:
    """
    增强型 SolidWorks 处理器
    集成了 DXF 导出功能
    """
    
    def __init__(self, sw_version: str = "2024"):
        """初始化处理器"""
        self.sw_version = sw_version
        self.sw_app = None
        self.dxf_exporter = None
    
    def connect(self):
        """连接到 SolidWorks"""
        try:
            import pySldWrap.sw_tools as sw
            sw.connect_sw(self.sw_version)
            
            # 获取 COM 对象
            self.sw_app = win32com.client.Dispatch("SldWorks.Application")
            
            # 初始化 DXF 导出器
            self.dxf_exporter = DXFExporter(self.sw_app)
            
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    # 集成所有功能
    def export_drawing_to_dxf(self, *args, **kwargs):
        """导出图纸为 DXF（委托给 DXFExporter）"""
        return self.dxf_exporter.export_drawing(*args, **kwargs)
    
    def batch_export_drawings_to_dxf(self, *args, **kwargs):
        """批量导出图纸为 DXF"""
        return self.dxf_exporter.batch_export_drawings(*args, **kwargs)
    
    def export_sheet_metal_to_dxf(self, *args, **kwargs):
        """导出钣金为 DXF"""
        return self.dxf_exporter.export_sheet_metal_flat_pattern(*args, **kwargs)
    
    def batch_export_sheet_metal_to_dxf(self, *args, **kwargs):
        """批量导出钣金为 DXF"""
        return self.dxf_exporter.batch_export_sheet_metal(*args, **kwargs)


# ==================== 使用示例 ====================

if __name__ == "__main__":
    processor = EnhancedSolidWorksProcessor("2024")
    
    if not processor.connect():
        print("无法连接到 SolidWorks")
        exit(1)
    
    print("✓ 已连接到 SolidWorks\n")
    
    # ========== 示例 1: 导出单个图纸 ==========
    print("示例 1: 导出单个图纸为 DXF")
    success = processor.export_drawing_to_dxf(
        drawing_path="C:/Projects/drawing.SLDDRW",
        output_path="C:/Output/drawing.dxf",
        export_format=ExportFormat.DXF
    )
    print(f"导出结果: {'成功' if success else '失败'}\n")
    
    # ========== 示例 2: 批量导出图纸 ==========
    print("示例 2: 批量导出图纸")
    drawings = [
        "C:/Projects/drawing1.SLDDRW",
        "C:/Projects/drawing2.SLDDRW",
        "C:/Projects/drawing3.SLDDRW"
    ]
    
    results = processor.batch_export_drawings_to_dxf(
        drawing_paths=drawings,
        output_dir="C:/Output/DXF",
        export_format=ExportFormat.DXF,
        progress_callback=lambda c, t, f: print(f"  [{c}/{t}] {Path(f).name}")
    )
    
    success_count = sum(1 for r in results if r["success"])
    print(f"✓ 完成: {success_count}/{len(results)} 成功\n")
    
    # ========== 示例 3: 导出钣金展开图 ==========
    print("示例 3: 批量导出钣金展开图")
    sheet_metal_parts = [
        "C:/Projects/bracket.SLDPRT",
        "C:/Projects/cover.SLDPRT"
    ]
    
    results = processor.batch_export_sheet_metal_to_dxf(
        part_paths=sheet_metal_parts,
        output_dir="C:/Output/SheetMetal",
        export_format=ExportFormat.DXF,
        options=DXFExportOptions(
            include_bend_lines=True,
            include_sketches=False
        ),
        progress_callback=lambda c, t, f: print(f"  [{c}/{t}] {Path(f).name}")
    )
    
    print(f"✓ 钣金导出完成\n")
    
    # ========== 示例 4: 导出草图 ==========
    print("示例 4: 导出草图为 DXF")
    success = processor.dxf_exporter.export_sketch_to_dxf(
        model_path="C:/Projects/part.SLDPRT",
        sketch_name="Sketch1",
        output_path="C:/Output/sketch.dxf"
    )
    print(f"草图导出: {'成功' if success else '失败'}\n")
    
    print("=" * 60)
    print("所有示例完成！")
    print("=" * 60)