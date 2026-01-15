# app/set_template.py
import sys
from pathlib import Path

from utils import ref_int, Show, logger

class SetTemplate:
    
    @staticmethod
    def get_template_dir():
        """获取模板目录（EXE 同级 template 文件夹）"""
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后
            base_path = Path(sys.executable).parent
        else:
            # 开发环境
            base_path = Path(__file__).parent.parent
        
        logger.info(f"程序目录: {base_path}")

        template_dir = base_path / "template"
        
        if not template_dir.exists():
            raise FileNotFoundError(f"未找到模板文件夹：{template_dir}")
        
        return template_dir

    @staticmethod
    def replace_template_and_format(sw_app, sw_model):
        """替换图纸模板 & 统一标注图层"""

        TARGET_LAYER = "标注层"
        TOLERANCE = 0.001

        # 图纸尺寸映射 (米)
        SHEET_SIZES = {
            (1.189, 0.841): "a0图纸格式.slddrt",  # A0
            (0.841, 0.594): "a1图纸格式.slddrt",  # A1
            (0.594, 0.420): "a2图纸格式.slddrt",  # A2
            (0.420, 0.297): "a3图纸格式.slddrt",  # A3
            (0.420, 0.294): "a3图纸格式.slddrt",  # A3 变体
            (0.297, 0.210): "a4图纸格式.slddrt",  # A4 横向
            (0.210, 0.297): "a4图纸格式-竖.slddrt",  # A4 竖向
        }

        try:
            logger.info("开始替换模板")
            
            # 检查是否为工程图
            if sw_model.GetType != 3:  # swDocDRAWING = 3
                # Show.message_box("错误", "当前文档不是工程图！", 16)
                logger.error("当前文档不是工程图！")
                return False
            
            sw_draw = sw_model
            
            # 获取模板目录
            template_dir = SetTemplate.get_template_dir()
            draft_std = template_dir / "GB-3.5新-小箭头.sldstd"
            
            logger.info(f"模板目录: {template_dir}")
            
            # 获取当前图纸
            sheet = sw_draw.GetCurrentSheet
            sheet_props = sheet.GetProperties2
            
            width = sheet_props[5]
            height = sheet_props[6]
            
            logger.info(f"图纸尺寸: {width:.3f} x {height:.3f}")
            
            # 选择对应的图纸格式
            format_file = None
            for (w, h), filename in SHEET_SIZES.items():
                if abs(width - w) < TOLERANCE and abs(height - h) < TOLERANCE:
                    format_file = template_dir / filename
                    logger.info(f"匹配图纸格式: {filename}")
                    break
            
            if format_file and format_file.exists():
                sheet.SetTemplateName(str(format_file))
            else:
                logger.error(f"未识别的图纸尺寸或文件不存在: {width} x {height}")
            
            # 加载绘图标准
            if draft_std.exists():
                sw_draw.Extension.LoadDraftingStandard(str(draft_std))
            else:
                logger.error(f"绘图标准文件不存在: {draft_std}")
            
            # 重载图纸格式 
            sheet.ReloadTemplate(False)
            
            # 更换标注图层
            # num_sheets = sw_draw.GetSheetCount
            # print(f"需要更改 {num_sheets} 个图层")
            
            # for i in range(1, num_sheets + 1):
            #     print(f"DEBUG | sw_draw.GetSheetNames - {sw_draw.GetSheetNames[i-1]}")
            #     # 切换到当前图纸
            #     sw_draw.ActivateSheet(str(sw_draw.GetSheetNames[i-1]))
                
            #     # 安全遍历视图
            #     sw_view = sw_draw.GetFirstView
            #     print(f"DEBUG | GetFirstView - {sw_view}")
            #     while sw_view:
            #         sw_dim = sw_view.GetFirstDisplayDimension
            #         print(f"DEBUG | GetFirstDisplayDimension - {sw_dim}")
            #         while sw_dim:
            #             sw_ann = sw_dim.GetAnnotation
            #             print(f"DEBUG | GetAnnotation - {sw_ann}")
            #             if sw_ann:
            #                 sw_ann.Layer = TARGET_LAYER
                        
            #             try:
            #                 sw_dim = sw_dim.GetNext3
            #             except:
            #                 sw_dim = None # 防止死循环
                    
            #         try:
            #             sw_view = sw_view.GetNextView
            #         except:
            #             sw_view = None # 安全退出循环

            # 保存
            # errors = ref_int()
            # warnings = ref_int()
            # sw_draw.Save3(1, errors, warnings)  # swSaveAsOptions_Silent = 1
            
            logger.info("替换模板完成")
            return True
            
        except Exception as e:
            logger.error(f"错误: {str(e)}")
            return False