# core/sw_converter.py
import os
import sys
from pathlib import Path
from typing import Optional, Tuple
import win32com.client as win32
import pythoncom

from utils import logger


class SWConverter:
    """SolidWorks DXF转换器"""
    
    def __init__(self):
        self.sw_app = None
        self.template_dir: Path
        self._initialize_template_dir()
    
    def _initialize_template_dir(self):
        """初始化模板目录"""
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent

        logger.info(f"程序目录: {base_path}")
        
        self.template_dir = base_path / "template"

        if not self.template_dir.exists():
            raise FileNotFoundError(f"未找到模板文件夹：{self.template_dir}")
    
    def initialize(self) -> bool:
        """初始化SolidWorks应用"""
        try:
            pythoncom.CoInitialize()
            try:
                self.sw_app = win32.GetActiveObject("SldWorks.Application")
            except:
                self.sw_app = win32.Dispatch("SldWorks.Application")
                self.sw_app.Visible = False
            return True
        except Exception as e:
            print(f"初始化SolidWorks失败: {e}")
            return False
    
    def shutdown(self):
        """关闭SolidWorks连接"""
        try:
            self.sw_app = None
            pythoncom.CoUninitialize()
        except:
            pass
    
    def convert_to_dxf(self, slddrw_path: Path, output_path: Path) -> Tuple[bool, str]:
        """
        将SLDDRW文件转换为DXF
        
        Args:
            slddrw_path: SLDDRW文件路径
            output_path: DXF输出路径
        
        Returns:
            (成功标志, 消息)
        """
        if not self.sw_app:
            return False, "SolidWorks未初始化"
        
        logger.info(f"正在处理: {os.path.basename(slddrw_path)}")
        logger.info(f"完整路径: {slddrw_path}")
        
        try:
            # 打开文档
            errors = self._create_ref_int()
            warnings = self._create_ref_int()
            
            sw_model = self.sw_app.OpenDoc6(
                str(slddrw_path),
                3,  # swDocDRAWING
                1,  # swOpenDocOptions_Silent
                "",
                errors,
                warnings
            )
            
            if sw_model is None:
                logger.error("无法打开文件")
                return False, f"无法打开文件: {slddrw_path.name}"
            
            title = sw_model.GetTitle
            logger.info(f"连接到文档：{title}")
            
            # 执行处理步骤
            # 1. 设置视图比例
            self._set_views_to_sheet_scale(sw_model)
            
            # 2. 替换模板
            self._replace_template(sw_model)
            
            # 3. 导出DXF
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sw_model.SaveAs2(str(output_path), 0, True, False)
            
            # 关闭文档
            self.sw_app.CloseDoc(str(slddrw_path))
            
            return True, f"✅ 成功转换: {slddrw_path.name}"
            
        except Exception as e:
            return False, f"❌ 转换失败 [{slddrw_path.name}]: {str(e)}"
    
    def _set_views_to_sheet_scale(self, sw_model) -> bool:
        """设置所有视图按图纸比例"""
        try:
            sw_view = sw_model.GetFirstView
            
            if sw_view is not None:
                sw_view = sw_view.GetNextView
            
            view_count = 0
            while sw_view is not None:
                sw_view.UseSheetScale = True
                view_count += 1
                sw_view = sw_view.GetNextView
            
            sw_model.EditRebuild3
            logger.info(f"已设置 {view_count} 个视图使用图纸比例")
            logger.info("设置视图比例完成")

            return True
        
        except Exception as e:
            logger.error(f"错误: {str(e)}")
            return False
    
    def _replace_template(self, sw_model) -> bool:
        """替换图纸模板"""
        TOLERANCE = 0.001
        
        SHEET_SIZES = {
            (1.189, 0.841): "a0图纸格式.slddrt",
            (0.841, 0.594): "a1图纸格式.slddrt",
            (0.594, 0.420): "a2图纸格式.slddrt",
            (0.420, 0.297): "a3图纸格式.slddrt",
            (0.420, 0.294): "a3图纸格式.slddrt",
            (0.297, 0.210): "a4图纸格式.slddrt",
            (0.210, 0.297): "a4图纸格式-竖.slddrt",
        }
        
        try:
            logger.info("开始替换模板")

            # 检查是否为工程图
            if sw_model.GetType != 3:
                logger.error("当前文档不是工程图！")
                return False
            
            # 获取模板目录
            logger.info(f"模板目录: {self.template_dir}")
            
            # 获取当前图纸
            sheet = sw_model.GetCurrentSheet
            sheet_props = sheet.GetProperties
            
            width = sheet_props[5]
            height = sheet_props[6]
            logger.info(f"图纸尺寸: {width:.3f} x {height:.3f}")

            # 选择对应的图纸格式
            format_file = None
            for (w, h), filename in SHEET_SIZES.items():
                if abs(width - w) < TOLERANCE and abs(height - h) < TOLERANCE:
                    format_file = self.template_dir / filename
                    logger.info(f"匹配图纸格式: {filename}")
                    break
            
            if format_file and format_file.exists():
                sheet.SetTemplateName(str(format_file))
            else:
                logger.error(f"未识别的图纸尺寸或文件不存在: {width} x {height}")
            
            draft_std = self.template_dir / "GB-3.5新-小箭头.sldstd"
            if draft_std.exists():
                sw_model.Extension.LoadDraftingStandard(str(draft_std))
            else:
                logger.error(f"绘图标准文件不存在: {draft_std}")
            
            sheet.ReloadTemplate(False)
            
            return True
        except:
            return False
    
    @staticmethod
    def _create_ref_int():
        """创建COM引用类型"""
        import win32com.client
        return win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)