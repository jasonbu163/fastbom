"""
SolidWorks 工程图自动化工具 - Python 版
功能：1. 替换图纸模板和格式 → 2. 设置所有视图按图纸比例 → 3. 导出 DXF
"""

import os
import sys
import win32com.client
from pathlib import Path
import ctypes


def get_template_dir():
    """获取模板目录（EXE 同级 template 文件夹）"""
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        base_path = Path(sys.executable).parent
    else:
        # 开发环境
        base_path = Path(__file__).parent
    
    template_dir = base_path / "template"
    
    if not template_dir.exists():
        raise FileNotFoundError(f"未找到模板文件夹：{template_dir}")
    
    return template_dir


def show_message(title, message, icon=0):
    """显示 Windows 消息框"""
    ctypes.windll.user32.MessageBoxW(0, message, title, icon)


def step1_replace_template_and_format(sw_app, sw_model):
    """Step 1: 替换图纸模板 & 统一标注图层"""

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
        print("开始 Step 1: 替换模板...")
        
        # 检查是否为工程图
        if sw_model.GetType() != 3:  # swDocDRAWING = 3
            show_message("错误", "当前文档不是工程图！", 16)
            return False
        
        sw_draw = sw_model
        
        # 获取模板目录
        template_dir = get_template_dir()
        draft_std = template_dir / "GB-3.5新-小箭头.sldstd"
        
        print(f"模板目录: {template_dir}")
        
        # 获取当前图纸
        sheet = sw_draw.GetCurrentSheet()
        sheet_props = sheet.GetProperties2()
        
        width = sheet_props[5]
        height = sheet_props[6]
        
        print(f"图纸尺寸: {width:.3f} x {height:.3f}")
        
        # 选择对应的图纸格式
        format_file = None
        for (w, h), filename in SHEET_SIZES.items():
            if abs(width - w) < TOLERANCE and abs(height - h) < TOLERANCE:
                format_file = template_dir / filename
                print(f"匹配图纸格式: {filename}")
                break
        
        if format_file and format_file.exists():
            sheet.SetTemplateName(str(format_file))
        else:
            print(f"未识别的图纸尺寸或文件不存在: {width} x {height}")
        
        # 加载绘图标准
        if draft_std.exists():
            sw_draw.Extension.LoadDraftingStandard(str(draft_std))
        else:
            print(f"警告：绘图标准文件不存在: {draft_std}")
        
        # 重载图纸格式
        sheet.ReloadTemplate(False)
        
        # 更换标注图层
        num_sheets = sw_draw.GetSheetCount()
        
        for i in range(num_sheets):
            sw_view = sw_draw.GetFirstView()
            while sw_view is not None:
                sw_dim = sw_view.GetFirstDisplayDimension()
                while sw_dim is not None:
                    sw_ann = sw_dim.GetAnnotation()
                    if sw_ann is not None:
                        sw_ann.Layer = TARGET_LAYER
                    sw_dim = sw_dim.GetNext3()
                sw_view = sw_view.GetNextView()
            
            if i < num_sheets - 1:
                sw_draw.SheetNext()
        
        # 保存
        sw_draw.Save3(1, 0, 0)  # swSaveAsOptions_Silent = 1
        
        print("Step 1 完成")
        return True
        
    except Exception as e:
        show_message("Step 1 错误", f"替换模板失败：\n{str(e)}", 16)
        print(f"Step 1 错误: {e}")
        return False


def step2_set_views_to_sheet_scale(sw_app, sw_model):
    """Step 2: 设置所有视图按图纸比例"""
    try:
        print("开始 Step 2: 设置视图比例...")
        
        sw_draw = sw_model
        sw_view = sw_draw.GetFirstView()
        
        # 跳过图纸视图
        if sw_view is not None:
            sw_view = sw_view.GetNextView()
        
        view_count = 0
        while sw_view is not None:
            sw_view.UseSheetScale = True
            view_count += 1
            sw_view = sw_view.GetNextView()
        
        sw_draw.EditRebuild3()
        
        print(f"已设置 {view_count} 个视图使用图纸比例")
        print("Step 2 完成")
        return True
        
    except Exception as e:
        show_message("Step 2 错误", f"设置视图比例失败：\n{str(e)}", 16)
        print(f"Step 2 错误: {e}")
        return False


def step3_export_dxf(sw_app, sw_model):
    """Step 3: 导出 DXF"""
    try:
        print("开始 Step 3: 导出 DXF...")
        
        draw_path = sw_model.GetPathName()
        
        if not draw_path:
            show_message("错误", "工程图尚未保存，无法导出 DXF\n请先保存工程图文件", 48)
            return False
        
        draw_path = Path(draw_path)
        export_dir = draw_path.parent / "dxf"
        
        # 创建导出目录
        export_dir.mkdir(exist_ok=True)
        
        # 构建 DXF 文件路径
        dxf_path = export_dir / f"{draw_path.stem}.DXF"
        
        # 导出 DXF
        sw_model.SaveAs2(str(dxf_path), 0, True, False)
        
        print(f"DXF 已导出: {dxf_path}")
        print("Step 3 完成")
        return True
        
    except Exception as e:
        show_message("Step 3 错误", f"DXF 导出失败：\n{str(e)}", 16)
        print(f"Step 3 错误: {e}")
        return False


def main():
    """主工作流"""
    print("=" * 60)
    print("SolidWorks 工程图自动化工具 - Python 版")
    print("=" * 60)
    
    try:
        # 连接到 SolidWorks
        print("正在连接 SolidWorks...")
        sw_app = win32com.client.Dispatch("SldWorks.Application")
        sw_model = sw_app.ActiveDoc
        
        if sw_model is None:
            show_message("错误", "未找到打开的 SolidWorks 文档", 16)
            return
        
        print(f"已连接到文档: {sw_model.GetTitle()}")
        
        # 执行三个步骤
        steps = [
            ("替换模板", step1_replace_template_and_format),
            ("设置视图比例", step2_set_views_to_sheet_scale),
            ("导出 DXF", step3_export_dxf),
        ]
        
        for step_name, step_func in steps:
            if not step_func(sw_app, sw_model):
                show_message("工作流中止", f"{step_name} 失败，工作流中止", 48)
                return
        
        # 全部成功
        message = (
            "Success! 工程图自动化处理完成！\n\n"
            "Step 1: 模板已替换\n"
            "Step 2: 视图比例已设置\n"
            "Step 3: DXF 已导出"
        )
        show_message("完成", message, 64)
        print("\n" + "=" * 60)
        print("全部步骤完成！")
        print("=" * 60)
        
    except Exception as e:
        show_message("错误", f"程序执行失败：\n{str(e)}", 16)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()