# build.py - FastBom 应用打包脚本
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
    ONEFILE = True      # True=单exe文件, False=文件夹形式
    WINDOWED = True     # True=隐藏控制台, False=显示控制台(调试时用False)
    # ==================================
    
    print("\n" + "=" * 60)
    print(f"FastBom 应用打包工具")
    print("=" * 60)
    
    # 检查主文件
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ 错误: 未找到主文件 {MAIN_SCRIPT}")
        return False
    print(f"✓ 主文件: {MAIN_SCRIPT}")
    
    # 检查图标
    if os.path.exists(ICON_PATH):
        print(f"✓ 图标文件: {ICON_PATH}")
    else:
        print(f"⚠ 未找到图标文件，将使用默认图标")
        ICON_PATH = None
    
    # 构建 PyInstaller 命令
    cmd = [
        'pyinstaller',
        '--clean',
        '--name', APP_NAME,
    ]
    
    # 打包模式
    if ONEFILE:
        cmd.append('--onefile')
        print(f"✓ 打包模式: 单文件")
    else:
        cmd.append('--onedir')
        print(f"✓ 打包模式: 文件夹")
    
    # 控制台模式
    if WINDOWED:
        cmd.append('--windowed')
        print(f"✓ 控制台: 隐藏")
    else:
        cmd.append('--console')
        print(f"✓ 控制台: 显示")
    
    # 图标
    if ICON_PATH:
        cmd.extend(['--icon', ICON_PATH])
    
    # 隐藏导入（确保所有依赖都被打包）
    hidden_imports = [
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'pandas',
        'ezdxf',
        'ezdxf.addons.importer',
        'qt_material',
        'openpyxl',  # pandas读Excel需要
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    # 添加 qt-material 主题文件
    try:
        import qt_material
        qt_material_path = Path(qt_material.__file__).parent
        cmd.extend(['--add-data', f'{qt_material_path}{os.pathsep}qt_material'])
        print(f"✓ 包含 qt-material 主题")
    except ImportError:
        print(f"⚠ 未检测到 qt-material，跳过主题打包")
    
    # 添加静态资源文件夹（如果存在）
    if os.path.exists('static'):
        cmd.extend(['--add-data', f'static{os.pathsep}static'])
        print(f"✓ 包含 static 文件夹")
    
    # 排除不需要的模块（减小体积）
    exclude = ['matplotlib', 'scipy', 'PIL', 'tkinter', 'test', 'unittest']
    for mod in exclude:
        cmd.extend(['--exclude-module', mod])
    
    # 添加主脚本
    cmd.append(MAIN_SCRIPT)
    
    # 开始打包
    print("\n" + "=" * 60)
    print("正在打包，请稍候...")
    print("=" * 60 + "\n")
    
    try:
        subprocess.run(cmd, check=True)
        
        # 打包成功
        print("\n" + "=" * 60)
        print("🎉 打包成功！")
        print("=" * 60)
        
        if ONEFILE:
            exe_path = f"dist/{APP_NAME}.exe"
        else:
            exe_path = f"dist/{APP_NAME}/{APP_NAME}.exe"
        
        print(f"\n📦 可执行文件: {exe_path}")
        print(f"📂 文件大小: {os.path.getsize(exe_path) / (1024*1024):.1f} MB")
        
        print("\n💡 使用提示:")
        print("1. 直接双击运行 exe 文件")
        print("2. 首次分发给他人时，建议先测试运行")
        print("3. 如果遇到问题，可以修改 WINDOWED=False 查看控制台错误")
        
        return True
        
    except subprocess.CalledProcessError:
        print("\n❌ 打包失败！")
        print("\n💡 调试建议:")
        print("1. 设置 WINDOWED = False 查看详细错误")
        print("2. 设置 ONEFILE = False 使用文件夹模式（更稳定）")
        print("3. 确保所有依赖都已正确安装")
        return False

if __name__ == '__main__':
    print("FastBom 打包工具 v1.0\n")
    
    # 检查 PyInstaller
    if not check_pyinstaller():
        print("❌ 缺少 PyInstaller，无法继续")
        sys.exit(1)
    
    # 执行打包
    success = build_app()
    
    if success:
        print("\n✅ 打包流程完成！\n")
    else:
        print("\n❌ 打包失败，请检查错误信息\n")
        sys.exit(1)