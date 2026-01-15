# app/file_export.py
from pathlib import Path
from utils import Show, logger

class FileExport:

    @staticmethod
    def to_dxf(sw_app, sw_model):
        """导出dxf"""
        try:
            logger.info("开始导出dxf")

            draw_path = sw_model.GetPathName

            if not draw_path:
                Show.message_box("错误", "工程图尚未保存，无法导出 DXF\n请先保存工程图文件", 48)
                return
            
            draw_path = Path(draw_path)
            export_dir = draw_path.parent / "dxf"

            export_dir.mkdir(exist_ok=True)

            dxf_path = export_dir / f"{draw_path.stem}.DXF"

            sw_model.SaveAs2(str(dxf_path), 0, True, False)

            logger.info(f"DXF 已导出：{dxf_path}")
            logger.info("导出 DXF 完成")
            return True
        
        except Exception as e:
            Show.message_box("错误", f"DXF 导出失败：\n{str(e)}", 16)
            logger.error(f"错误: {str(e)}")
            return False