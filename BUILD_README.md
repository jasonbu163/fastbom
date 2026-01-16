# FastBOM 整合版 - 打包说明

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
