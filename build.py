# build.py - NiceGUI 应用打包脚本
import os
import subprocess
import sys
from pathlib import Path

def install_dependencies():
    """检查并安装必要的依赖包"""
    dependencies = ['pyinstaller']
    
    # 检查是否安装了 pywebview（如果使用 native=True 则需要）
    try:
        import webview
    except ImportError:
        print("提示：如果您计划使用 ui.run(native=True)，请先安装 pywebview：")
        print("pip install pywebview")
    
    for package in dependencies:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ 已安装 {package}")
        except ImportError:
            print(f"正在安装缺失的依赖: {package}")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])

def build_with_pyinstaller(main_script='main.py', app_name='MyNiceGUIApp', onefile=True, windowed=True, icon_path=None):
    """
    使用 PyInstaller 打包 NiceGUI 应用
    
    参数:
        main_script: 主程序文件路径
        app_name: 生成的应用程序名称
        onefile: 是否打包为单文件
        windowed: 是否隐藏控制台窗口
        icon_path: 图标文件路径(.ico)
    """
    
    # 获取 nicegui 包的路径
    import nicegui
    
    # 构建 PyInstaller 命令
    cmd = [
        'pyinstaller',
        main_script,
        '--name', app_name,
        '--clean',  # 清理临时文件
    ]
    
    # 添加常用参数
    if onefile:
        cmd.append('--onefile')
    
    if windowed:
        cmd.append('--windowed')
    
    if icon_path and os.path.exists(icon_path):
        cmd.extend(['--icon', icon_path])
        print(f"✓ 使用图标: {icon_path}")
    
    # 添加 nicegui 静态资源（这是关键步骤！）
    nicegui_path = Path(nicegui.__file__).parent
    cmd.extend([
        '--add-data', f'{nicegui_path}{os.pathsep}nicegui'
    ])
    
    # 尝试添加 pywebview 资源（如果使用了 native=True）
    try:
        import webview
        webview_path = Path(webview.__file__).parent
        cmd.extend([
            '--add-data', f'{webview_path}{os.pathsep}webview'
        ])
        print("✓ 包含 pywebview 资源")
    except ImportError:
        print("ℹ️ 未检测到 pywebview，跳过 webview 资源包含")
    
    # 添加其他可能需要的手动导入
    hidden_imports = [
        'nicegui.elements',
        'nicegui.elements.scene',
        'nicegui.app',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    print("=" * 50)
    print("开始打包，请稍候...")
    print(f"主程序: {main_script}")
    print(f"应用名称: {app_name}")
    print(f"单文件模式: {onefile}")
    print(f"隐藏控制台: {windowed}")
    print("=" * 50)
    
    # 执行打包命令
    try:
        subprocess.run(cmd, check=True)
        print("🎉 打包完成！")
        print(f"可执行文件位置: ./dist/{app_name}.exe")
        
        # 显示后续步骤提示
        print("\n" + "=" * 50)
        print("📋 打包后注意事项:")
        print("1. 建议在干净的虚拟环境中打包以减少文件大小")
        print("2. 首次运行前，可在命令行中测试: ./dist/{}.exe".format(app_name))
        print("3. 如果遇到静态资源错误，请确认 --add-data 参数正确包含 nicegui 路径")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 打包过程出错: {e}")
        return False
    except FileNotFoundError:
        print("❌ 未找到 PyInstaller，请先安装: pip install pyinstaller")
        return False
    
    return True

def build_with_nicegui_pack(main_script='main.py', app_name='MyNiceGUIApp', onefile=True, icon_path=None):
    """
    使用 nicegui-pack 打包（官方推荐方式）
    """
    try:
        cmd = ['nicegui-pack']
        
        if onefile:
            cmd.append('--onefile')
        
        if icon_path:
            cmd.extend(['--icon', icon_path])
        
        cmd.extend(['--name', app_name, main_script])
        
        print("使用 nicegui-pack 打包...")
        subprocess.run(cmd, check=True)
        print("🎉 nicegui-pack 打包完成！")
        return True
        
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ nicegui-pack 打包失败或未安装，尝试使用 PyInstaller 方式")
        return False

if __name__ == '__main__':
    # 配置参数 - 根据您的需求修改这些值
    CONFIG = {
        'main_script': 'main.py',      # 您的主程序文件
        'app_name': 'MyNiceGUIApp',    # 生成的exe名称
        'onefile': True,               # 是否打包为单个exe文件
        'windowed': True,              # 是否隐藏控制台窗口
        'icon_path': None,             # 图标文件路径，如 'app.ico'
        'prefer_nicegui_pack': False,  # 是否优先使用 nicegui-pack
    }
    
    # 安装依赖
    install_dependencies()
    
    # 检查主文件是否存在
    if not os.path.exists(CONFIG['main_script']):
        print(f"❌ 错误: 未找到主文件 {CONFIG['main_script']}")
        print("请确保在正确的目录中运行此脚本，或修改 CONFIG 中的 main_script")
        sys.exit(1)
    
    # 执行打包
    success = False
    
    # 优先使用 nicegui-pack（如果配置且可用）
    if CONFIG['prefer_nicegui_pack']:
        success = build_with_nicegui_pack(
            CONFIG['main_script'],
            CONFIG['app_name'],
            CONFIG['onefile'],
            CONFIG['icon_path']
        )
    
    # 如果 nicegui-pack 不可用或失败，使用 PyInstaller
    if not success:
        success = build_with_pyinstaller(
            CONFIG['main_script'],
            CONFIG['app_name'],
            CONFIG['onefile'],
            CONFIG['windowed'],
            CONFIG['icon_path']
        )
    
    if success:
        print("\n✅ 打包流程完成！")
    else:
        print("\n❌ 打包失败，请检查错误信息")