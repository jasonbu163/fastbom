# Over-SolidWorks
# main.py
import os
import time
from pathlib import Path

import win32com.client as win32
import pythoncom

from utils import ref_int, Show, logger
from core import FileExport, SetViews, SetTemplate

STEPS = [
    ("STEP 1 | 恢复视图比例", SetViews.to_sheet_scale),
    ("STEP 2 | 替换图纸模板", SetTemplate.replace_template_and_format),
    ("STEP 3 | 导出 DXF", FileExport.to_dxf),
]

def get_sw_app():
    try:
        sw = win32.GetActiveObject("SldWorks.Application")
    except Exception:
        sw = win32.Dispatch("SldWorks.Application")
        sw.Visible = False
    return sw

def get_doc_type(filepath):
    """根据文件扩展名返回文档类型"""
    ext = os.path.splitext(filepath)[1].upper()
    type_map = {
        '.SLDPRT': 1,   # 零件
        '.SLDASM': 2,   # 装配体
        '.SLDDRW': 3    # 工程图
    }
    return type_map.get(ext, 1)

def get_solidworks_files(directory, extensions=None):
    """
    获取目录下所有SolidWorks文件
    
    Args:
        directory: 目标目录路径
        extensions: 文件扩展名列表，默认为所有SW文件
    
    Returns:
        list: 文件路径列表
    """
    if extensions is None:
        extensions = ['.SLDPRT', '.SLDASM', '.SLDDRW']
    
    files = []
    for ext in extensions:
        # 使用glob查找文件（不区分大小写）
        files.extend(Path(directory).glob(f'*{ext}'))
        files.extend(Path(directory).glob(f'*{ext.lower()}'))
    
    # 去重并转换为绝对路径字符串
    files = list(set([str(f.resolve()) for f in files]))
    return sorted(files)


def process_single_file(sw_app, filepath) -> bool:
    """
    处理单个文件（这里放你已经跑通的单文件处理逻辑）
    
    Args:
        sw_app: SolidWorks应用对象
        filepath: 文件路径
    
    Returns:
        bool: 是否处理成功
    """
    filepath = os.path.abspath(filepath)
    
    logger.info(f"正在处理: {os.path.basename(filepath)}")
    logger.info(f"完整路径: {filepath}")
    
    try:
        doc_type = get_doc_type(filepath)
        logger.info(f'文档类型 {doc_type}')

        # ✅ 创建 VARIANT 引用类型
        errors = ref_int()
        warnings = ref_int()

        # 打开文档
        sw_model = sw_app.OpenDoc6(
            filepath,
            get_doc_type(filepath),
            1,
            "",
            errors,
            warnings
        )

        if sw_model is None:
            logger.error("无法打开文件")
            Show.message_box("错误", "未找到打开的 SolidWorks 文档", 16)
            return False

        # ========== 处理逻辑开始 ==========
        title = sw_model.GetTitle
        logger.info(f"连接到文档：{title}")
        
        for step_name, step_func in STEPS:
            if not step_func(sw_app, sw_model):
                Show.message_box("工作流中止", f"{step_name} 失败，工作流中止", 48)
                return False
            
        # ========== 处理逻辑结束 ==========
        
        # 关闭文档
        sw_app.CloseDoc(filepath)
        
        logger.info("处理完成")
        return True
        
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return False
    
def batch_process_solidworks(sw_app, directory=None, recursive=False):
    """
    批量处理SolidWorks文件
    
    Args:
        directory: 目标目录，None则使用脚本所在目录
        recursive: 是否递归处理子目录
    """
    # 如果未指定目录，使用脚本所在目录
    if directory is None:
        directory = os.path.dirname(os.path.abspath(__file__))
    
    logger.info(f"目标目录: {directory}")
    
    # 获取所有SolidWorks文件
    if recursive:
        files = []
        for root, dirs, filenames in os.walk(directory):
            files.extend(get_solidworks_files(root))
    else:
        files = get_solidworks_files(
            directory=directory,
            extensions=".SLDDRW"
        )
    
    if not files:
        logger.warning("未找到SolidWorks文件！")
        return
    
    logger.info(f"找到 {len(files)} 个文件")
    
    # 连接SolidWorks
    logger.info("正在连接SolidWorks...")
    
    # 批量处理
    success_count = 0
    fail_count = 0
    
    start_time = time.time()
    
    for i, filepath in enumerate(files, 1):
        logger.info(f"\n[{i}/{len(files)}]", end=" ")
        
        if process_single_file(sw_app, filepath):
            success_count += 1
        else:
            fail_count += 1
        
        # 可选：每处理几个文件暂停一下
        time.sleep(0.5)
    
    # 统计结果
    elapsed_time = time.time() - start_time
    logger.info(f"处理完成！")
    logger.info(f"成功: {success_count} | 失败: {fail_count} | 总计: {len(files)}")
    logger.info(f"耗时: {elapsed_time:.2f} 秒")

def main():
    try:
        pythoncom.CoInitialize()

        logger.info("正在连接 SolidWorks...")
        sw_app = get_sw_app()
        
        # file_path = Path("source_file/SC06020102.01-06 折弯板.SLDDRW")
        # file_path_str = str(file_path)
        # logger.info(f"文件路径 - {file_path_str}")
        # process_single_file(sw_app=sw_app, filepath=file_path_str)

        file_dir = Path("source_file")
        file_dir_str = str(file_dir)
        logger.info(f"文件目录路径 - {file_dir_str}")
        batch_process_solidworks(sw_app=sw_app, directory=file_dir_str)
        
    except Exception as e:
        Show.message_box("错误", f"程序执行失败：\n{str(e)}", 16)
        logger.error(f"错误：{e}")
        import traceback
        traceback.print_exc()

    finally:
        pythoncom.CoUninitialize()

def main_gui():
    """启动GUI模式"""
    from gui import gui_main
    gui_main()

if __name__ == "__main__":
    import sys

    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # 命令行模式（带文件夹选择）
        main_gui()
    else:
        # GUI模式
        main_gui()