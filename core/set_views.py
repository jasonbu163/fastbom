# app/set_views.py
from utils import Show, logger

class SetViews:

    @staticmethod
    def to_sheet_scale(sw_app, sw_model):
        """设置所有视图按图纸比例"""
        try:
            logger.info("开始设置视图比例")
            
            sw_draw = sw_model
            sw_view = sw_draw.GetFirstView
            
            # 跳过图纸视图
            if sw_view is not None:
                sw_view = sw_view.GetNextView
            
            view_count = 0
            while sw_view is not None:
                sw_view.UseSheetScale = True
                view_count += 1
                sw_view = sw_view.GetNextView
            
            sw_draw.EditRebuild3
            
            logger.info(f"已设置 {view_count} 个视图使用图纸比例")
            logger.info("设置视图比例完成")
            return True
            
        except Exception as e:
            logger.error(f"错误: {str(e)}")
            return False