# build.py - FastBom 应用打包脚本 (已修复 NumPy 兼容性)
import os
import subprocess
import sys
from pathlib import Path

def check_pyinstaller():
    """检查 PyInstaller 是否安装"""
    try:
        import PyInstaller
        print(f"✓ PyInstaller 已安装 (版本 {PyInstaller.__version__})")
        return True
    except ImportError:
        print("✗ PyInstaller 未安装")
        install = input("是否自动安装 PyInstaller？(y/n): ").strip().lower()
        if install == 'y':
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            return True
        return False

def build_app():
    """打包 FastBom 应用"""
    
    # ============ 配置区域 ============
    MAIN_SCRIPT = 'main.py'
    APP_NAME = 'FastBom'
    ICON_PATH = 'static/efficacy_researching_settings_icon_152066.ico'
    # 如果单文件模式依然报错，请将 ONEFILE 改为 False 尝试文件夹模式
    ONEFILE = True      
    WINDOWED = True     
    # ==================================
    
    print("\n" + "=" * 60)
    print(f"FastBom 应用打包工具 (优化版)")
    print("=" * 60)
    
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ 错误: 未找到主文件 {MAIN_SCRIPT}")
        return False
    
    # 构建基础命令
    cmd = [
        'pyinstaller',
        '--clean',
        '--name', APP_NAME,
    ]
    
    # --- 【关键改动 1: 自动收集核心库的所有数据和模块】 ---
    # 这比手动写 hidden-import 更稳妥，能解决 NumPy C-extensions 丢失问题
    for lib in ['numpy', 'pandas', 'ezdxf']:
        cmd.extend(['--collect-all', lib])
    
    # 打包模式
    if ONEFILE:
        cmd.append('--onefile')
    else:
        cmd.append('--onedir')
    
    # 控制台模式
    if WINDOWED:
        cmd.append('--windowed')
    else:
        cmd.append('--console')
    
    # 图标
    if os.path.exists(ICON_PATH):
        cmd.extend(['--icon', ICON_PATH])
    
    # --- 【关键改动 2: 精简并补充 Hidden Imports】 ---
    hidden_imports = [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'openpyxl',
    ]
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # 添加静态资源
    try:
        import qt_material
        qt_material_path = Path(qt_material.__file__).parent
        cmd.extend(['--add-data', f'{qt_material_path}{os.pathsep}qt_material'])
    except ImportError:
        pass

    if os.path.exists('static'):
        cmd.extend(['--add-data', f'static{os.pathsep}static'])
    
    # 排除不需要的模块
    # exclude = ['matplotlib', 'scipy', 'PIL', 'tkinter', 'test', 'unittest']
    # for mod in exclude:
    #     cmd.extend(['--exclude-module', mod])
    
    cmd.append(MAIN_SCRIPT)
    
    print("\n🚀 正在执行命令:", " ".join(cmd))
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 打包成功！文件位于 dist 目录。")
        return True
    except subprocess.CalledProcessError:
        print("\n❌ 打包失败！")
        return False

if __name__ == '__main__':
    if check_pyinstaller():
        build_app()