# build.py - FastBOM 整合版打包脚本
"""
FastBOM 智能处理系统 v2.0 - 打包工具
功能：将 Python 项目打包为独立可执行文件
"""

import os
import subprocess
import sys
from pathlib import Path
import shutil


class Colors:
    """终端颜色输出"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    
    @classmethod
    def print_header(cls, text):
        print(f"\n{cls.HEADER}{cls.BOLD}{'=' * 60}{cls.ENDC}")
        print(f"{cls.HEADER}{cls.BOLD}{text:^60}{cls.ENDC}")
        print(f"{cls.HEADER}{cls.BOLD}{'=' * 60}{cls.ENDC}\n")
    
    @classmethod
    def print_success(cls, text):
        print(f"{cls.OKGREEN}✓ {text}{cls.ENDC}")
    
    @classmethod
    def print_info(cls, text):
        print(f"{cls.OKBLUE}ℹ {text}{cls.ENDC}")
    
    @classmethod
    def print_warning(cls, text):
        print(f"{cls.WARNING}⚠ {text}{cls.ENDC}")
    
    @classmethod
    def print_error(cls, text):
        print(f"{cls.FAIL}✗ {text}{cls.ENDC}")


def check_and_install_pyinstaller():
    """检查并安装 PyInstaller"""
    try:
        import PyInstaller
        Colors.print_success(f"PyInstaller 已安装 (版本 {PyInstaller.__version__})")
        return True
    except ImportError:
        Colors.print_warning("PyInstaller 未安装")
        install = input("  是否自动安装 PyInstaller？(y/n): ").strip().lower()
        if install == 'y':
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
                Colors.print_success("PyInstaller 安装成功")
                return True
            except subprocess.CalledProcessError:
                Colors.print_error("PyInstaller 安装失败")
                return False
        return False


def clean_build_files():
    """清理之前的构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = ['*.spec']
    
    Colors.print_info("清理旧的构建文件...")
    
    cleaned = False
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"  删除目录: {dir_name}")
            cleaned = True
    
    for pattern in files_to_clean:
        for file in Path('.').glob(pattern):
            file.unlink()
            print(f"  删除文件: {file}")
            cleaned = True
    
    if not cleaned:
        print("  无需清理")


def validate_project_structure():
    """验证项目结构"""
    Colors.print_info("验证项目结构...")
    
    required_files = {
        'main.py': '主程序入口',
        'core/bom_classifier.py': 'BOM分类器',
        'core/dxf_processor.py': 'DXF处理器',
        'core/sw_converter.py': 'SolidWorks转换器',
        'gui/main_window.py': '主窗口',
        'gui/worker_thread.py': '工作线程',
        'utils/show.py': '通用工具',
        'utils/log.py': '日志工具',
    }
    
    optional_dirs = {
        'template': '模板文件夹（SolidWorks模板）',
        'static': '静态资源（图标等）',
    }
    
    all_valid = True
    
    # 检查必需文件
    for file_path, desc in required_files.items():
        if os.path.exists(file_path):
            print(f"  ✓ {desc}: {file_path}")
        else:
            Colors.print_error(f"{desc}不存在: {file_path}")
            all_valid = False
    
    # 检查可选目录
    print()
    for dir_path, desc in optional_dirs.items():
        if os.path.exists(dir_path):
            file_count = len(list(Path(dir_path).rglob('*')))
            print(f"  ✓ {desc}: {dir_path} ({file_count} 个文件)")
        else:
            Colors.print_warning(f"{desc}不存在: {dir_path} (可选)")
    
    return all_valid


def copy_resources_to_dist():
    """复制资源文件到 dist 目录"""
    dist_path = Path('dist')
    if not dist_path.exists():
        return
    
    Colors.print_info("复制资源文件到 dist 目录...")
    
    resources_to_copy = {
        'template': 'SolidWorks模板文件',
        'static': '静态资源文件',
    }
    
    copied_count = 0
    for src_dir, desc in resources_to_copy.items():
        if os.path.exists(src_dir):
            dest_dir = dist_path / src_dir
            shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
            file_count = len(list(dest_dir.rglob('*')))
            print(f"  ✓ {desc}: {src_dir} → dist/{src_dir} ({file_count} 个文件)")
            copied_count += 1
    
    if copied_count == 0:
        print("  无资源文件需要复制")


def build_with_pyinstaller(config):
    """使用 PyInstaller 打包应用"""
    
    Colors.print_header("开始打包 FastBOM 整合版")
    
    # 构建基础命令
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        '--name', config['app_name'],
    ]
    
    # 打包模式
    if config['onefile']:
        cmd.append('--onefile')
        Colors.print_info("打包模式: 单文件 (.exe)")
    else:
        cmd.append('--onedir')
        Colors.print_info("打包模式: 文件夹")
    
    # 控制台模式
    if config['windowed']:
        cmd.append('--windowed')
        Colors.print_info("界面模式: GUI (无控制台窗口)")
    else:
        cmd.append('--console')
        Colors.print_info("界面模式: 控制台 + GUI")
    
    # 图标
    if config['icon_path'] and os.path.exists(config['icon_path']):
        cmd.extend(['--icon', config['icon_path']])
        Colors.print_success(f"应用图标: {config['icon_path']}")
    
    # ===== 核心依赖：自动收集所有数据和子模块 =====
    print()
    Colors.print_info("配置核心依赖...")
    
    core_libs = ['numpy', 'pandas', 'ezdxf', 'openpyxl']
    for lib in core_libs:
        cmd.extend(['--collect-all', lib])
        print(f"  ✓ 自动收集: {lib}")
    
    # ===== Hidden Imports =====
    print()
    Colors.print_info("配置 Hidden Imports...")
    
    hidden_imports = [
        # PySide6 核心模块
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        
        # Win32 COM 支持（SolidWorks）
        'win32com.client',
        'win32com.client.gencache',
        'pythoncom',
        'pywintypes',
        
        # 数据处理
        'openpyxl',
        'openpyxl.cell._writer',
        
        # 项目模块
        'core',
        'core.bom_classifier',
        'core.dxf_processor',
        'core.sw_converter',
        'gui',
        'gui.main_window',
        'gui.worker_thread',
        'utils',
        'utils.common',
        'utils.logger',
    ]
    
    for imp in hidden_imports:
        cmd.extend(['--hidden-import', imp])
    
    print(f"  ✓ 添加 {len(hidden_imports)} 个隐藏导入")
    
    # ===== 添加数据文件 =====
    print()
    Colors.print_info("配置数据文件...")
    
    data_files = []
    
    # qt_material 主题（如果安装）
    try:
        import qt_material
        qt_material_path = Path(qt_material.__file__).parent
        data_files.append((str(qt_material_path), 'qt_material'))
        print(f"  ✓ qt_material 主题")
    except ImportError:
        Colors.print_warning("qt_material 未安装，将使用默认主题")
    
    # 项目资源
    if os.path.exists('template'):
        data_files.append(('template', 'template'))
        print(f"  ✓ template 目录")
    
    if os.path.exists('static'):
        data_files.append(('static', 'static'))
        print(f"  ✓ static 目录")
    
    for src, dest in data_files:
        cmd.extend(['--add-data', f'{src}{os.pathsep}{dest}'])
    
    # ===== 排除不需要的模块（可选，减小体积）=====
    if config.get('optimize_size', False):
        print()
        Colors.print_info("优化体积：排除不需要的模块...")
        
        exclude_modules = [
            'matplotlib',
            'scipy',
            'PIL',
            'tkinter',
            'test',
            'unittest',
            'IPython',
            'jupyter',
            'notebook',
        ]
        
        for mod in exclude_modules:
            cmd.extend(['--exclude-module', mod])
        
        print(f"  ✓ 排除 {len(exclude_modules)} 个模块")
    
    # 添加主脚本
    cmd.append(config['main_script'])
    
    # ===== 执行打包 =====
    print()
    Colors.print_header("执行 PyInstaller")
    
    print("命令预览:")
    print(f"  {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        
        Colors.print_header("打包成功！")
        
        # 显示输出位置
        if config['onefile']:
            output_path = f"./dist/{config['app_name']}.exe"
            
            # 显示文件大小
            exe_path = Path(output_path)
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                Colors.print_success(f"输出文件: {output_path}")
                Colors.print_info(f"文件大小: {size_mb:.2f} MB")
        else:
            output_path = f"./dist/{config['app_name']}/"
            Colors.print_success(f"输出目录: {output_path}")
        
        # 复制资源文件
        print()
        copy_resources_to_dist()
        
        return True
        
    except subprocess.CalledProcessError as e:
        Colors.print_header("打包失败")
        Colors.print_error(f"错误信息: {e}")
        print("\n常见问题排查:")
        print("  1. 检查是否所有依赖都已安装")
        print("  2. 尝试使用 --console 模式查看详细错误")
        print("  3. 检查 PyInstaller 版本: pip install --upgrade pyinstaller")
        return False


def create_requirements_file():
    """创建 requirements.txt 文件"""
    Colors.print_info("生成 requirements.txt...")
    
    requirements = [
        "# FastBOM 整合版 - 依赖清单",
        "",
        "# GUI 框架",
        "PySide6>=6.6.0",
        "",
        "# 数据处理",
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "",
        "# DXF 处理",
        "ezdxf>=1.1.0",
        "",
        "# SolidWorks COM 接口",
        "pywin32>=305",
        "",
        "# 主题（可选）",
        "qt-material>=2.14",
        "",
        "# 打包工具（开发时）",
        "pyinstaller>=6.0.0",
    ]
    
    with open('requirements.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(requirements))
    
    Colors.print_success("已创建 requirements.txt")


def create_build_readme():
    """创建打包说明文档"""
    Colors.print_info("生成 BUILD_README.md...")
    
    readme_content = """# FastBOM 整合版 - 打包说明

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行打包脚本
```bash
python build.py
```

### 3. 查看输出
- **单文件模式**: `dist/FastBOM.exe`
- **文件夹模式**: `dist/FastBOM/`

---

## 打包配置

编辑 `build.py` 中的 `CONFIG` 字典:

```python
CONFIG = {
    'main_script': 'main.py',           # 主程序入口
    'app_name': 'FastBOM',              # 应用名称
    'icon_path': 'static/icon.ico',     # 应用图标
    'onefile': True,                    # True=单文件, False=文件夹
    'windowed': True,                   # True=无控制台, False=显示控制台
    'optimize_size': False,             # True=排除不需要的模块
}
```

---

## 系统要求

### 开发环境
- Python 3.8+
- Windows 操作系统
- SolidWorks (用于 COM 接口开发)

### 目标机器要求
- Windows 7/10/11
- **必须安装 SolidWorks** (用于 DXF 转换功能)
- 建议以管理员权限运行 (COM 调用需要)

---

## 项目结构

```
fastbom_integrated/
├── main.py                 # 主程序入口
├── core/                   # 核心业务逻辑
│   ├── bom_classifier.py
│   ├── dxf_processor.py
│   └── sw_converter.py
├── gui/                    # GUI 界面
│   ├── main_window.py
│   └── worker_thread.py
├── utils/                  # 工具类
│   ├── common.py
│   └── logger.py
├── template/               # SolidWorks 模板文件
│   ├── GB-3.5新-小箭头.sldstd
│   ├── a0图纸格式.slddrt
│   └── ...
└── static/                 # 静态资源
    └── icon.ico
```

---

## 常见问题

### 1. 打包后运行报错 "无法找到模块"
**解决方案**: 在 `build.py` 的 `hidden_imports` 中添加缺失的模块

### 2. 打包文件过大
**解决方案**:
- 设置 `optimize_size: True`
- 使用虚拟环境打包（只安装必要依赖）
- 考虑使用文件夹模式而非单文件模式

### 3. SolidWorks COM 错误
**解决方案**:
- 确保目标机器已安装 SolidWorks
- 以管理员权限运行程序
- 检查 SolidWorks 版本兼容性

### 4. NumPy C-extensions 丢失
**解决方案**: 使用 `--collect-all numpy` (已在脚本中配置)

---

## 高级选项

### 使用 UPX 压缩
```bash
pip install pyinstaller[upx]
```
在 `build.py` 中添加:
```python
cmd.append('--upx-dir=/path/to/upx')
```

### 多版本构建
```bash
# 控制台版本 (用于调试)
python build.py --console

# GUI 版本 (用于发布)
python build.py --windowed
```

---

## 测试建议

1. **本机测试**: 确保所有功能正常
2. **干净环境测试**: 在未安装 Python 的机器上测试
3. **不同 SolidWorks 版本测试**: 确保兼容性
4. **性能测试**: 使用大型 BOM 表和多个工程图文件

---

## 分发清单

打包完成后，分发以下内容:

### 单文件模式
```
FastBOM.exe
template/          (必需 - SolidWorks 模板)
static/            (可选 - 图标等资源)
使用说明.pdf       (建议附带)
```

### 文件夹模式
```
FastBOM/           (整个文件夹)
├── FastBOM.exe
├── template/
└── static/
使用说明.pdf
```

---

## 技术支持

如遇到问题:
1. 查看 `BUILD_README.md` 常见问题部分
2. 检查 PyInstaller 日志文件
3. 使用控制台模式运行，查看详细错误信息

---

## 许可证

[根据项目实际情况填写]
"""
    
    with open('BUILD_README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    Colors.print_success("已创建 BUILD_README.md")


def print_usage_guide(config):
    """打印使用指南"""
    Colors.print_header("使用指南")
    
    print("📋 下一步操作:\n")
    
    if config['onefile']:
        output = f"dist/{config['app_name']}.exe"
    else:
        output = f"dist/{config['app_name']}/"
    
    print(f"1. 测试运行:")
    print(f"   {output}\n")
    
    print("2. 功能测试:")
    print("   - 准备测试数据 (BOM 表 + SLDDRW 文件)")
    print("   - 测试完整工作流程")
    print("   - 检查输出结果\n")
    
    print("3. 分发准备:")
    print("   - 确保包含 template 文件夹 (SolidWorks 模板)")
    print("   - 准备使用说明文档")
    print("   - 说明系统要求 (需要安装 SolidWorks)\n")
    
    print("⚠️  重要提示:")
    print("   • 目标机器必须安装 SolidWorks")
    print("   • 建议以管理员权限运行")
    print("   • 首次运行可能需要初始化 COM 组件\n")


def main():
    """主函数"""
    
    # ============ 配置区域 ============
    CONFIG = {
        'main_script': 'main.py',
        'app_name': 'FastBOM',
        'icon_path': 'static/efficacy_researching_settings_icon_152066.ico',
        'onefile': True,        # True=单文件 .exe, False=文件夹
        'windowed': True,       # True=无控制台, False=显示控制台（调试推荐）
        'optimize_size': False, # True=排除不需要的模块以减小体积
    }
    # ==================================
    
    Colors.print_header("FastBOM 整合版 - 打包工具")
    
    # 1. 验证项目结构
    if not validate_project_structure():
        Colors.print_error("项目结构验证失败，请检查缺失的文件")
        return False
    
    print()
    
    # 2. 检查 PyInstaller
    if not check_and_install_pyinstaller():
        Colors.print_error("PyInstaller 未就绪，无法继续")
        return False
    
    print()
    
    # 3. 清理旧文件
    clean_build_files()
    
    print()
    
    # 4. 生成辅助文件
    create_requirements_file()
    create_build_readme()
    
    print()
    
    # 5. 执行打包
    success = build_with_pyinstaller(CONFIG)
    
    if success:
        print()
        print_usage_guide(CONFIG)
        Colors.print_success("打包流程完成！")
        return True
    else:
        Colors.print_error("打包失败，请查看错误信息")
        return False


if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        Colors.print_error(f"未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)