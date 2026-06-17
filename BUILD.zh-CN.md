# PMMS 3.0 Windows 打包说明

本文说明如何从当前 FastBOM 仓库打包 PMMS 3.0 桌面客户端。交付产物是一个
PySide6 Windows 操作台，用于 BOM 处理、SolidWorks COM 转换、DXF 后处理以及
远程物料库存工作流。

正式发布包必须在 Windows 上构建。macOS 或 Linux 可以做语法检查和界面冒烟检查，
但不能验证 SolidWorks COM 链路。

## 环境准备

- Windows 10 或 Windows 11。
- Python 3.13。
- 使用 `uv` 管理项目环境。
- 构建和验证机器已安装并授权 SolidWorks。
- 使用项目工作流安装依赖：

```bash
uv sync
```

项目通过 `pywin32` 声明 Windows 专用 COM 依赖；不要把 Agent 辅助工具依赖安装进
项目 `.venv`。

## 打包前检查

先执行轻量编译检查：

```bash
uv run python -m compileall main.py config core gui utils build.py
```

在支持 GUI 的 Windows 机器上，还需要启动桌面应用：

```bash
uv run python main.py
```

正式发布前，应使用一个小型 BOM 和 SolidWorks 工程图样例验证本地处理主链路。

## 打包命令

可执行文件名、打包名称、窗口标题和版本号来自 `config/app_metadata.py`：

```python
APP_NAME = "PMMS"
APP_VERSION = "3.0"
WINDOW_TITLE = "生产物料管理系统"
```

当产品名称或显示版本变化时，先修改这些元数据常量；`build.py` 会读取它们，不再
单独硬编码一份产品名。

默认发布包：

```bash
uv run python build.py
```

带控制台窗口的调试包：

```bash
uv run python build.py --console
```

文件夹模式，适合排查 DLL 或数据文件缺失：

```bash
uv run python build.py --onedir --console
```

非 Windows 冒烟打包，仅用于检查 PyInstaller 配置：

```bash
uv run python build.py --allow-non-windows
```

不要把非 Windows 打包结果当作正式交付产物。

## 输出产物

按当前元数据，默认单文件模式为：

```text
dist/
├── PMMS.exe
├── static/
└── template/
```

按当前元数据，文件夹模式为：

```text
dist/
└── PMMS/
    ├── PMMS.exe
    ├── static/
    └── template/
```

`template/` 会复制到可执行文件旁边，确保交付包不依赖源码目录。操作员和现场支持
人员应能明确查看或替换 SolidWorks 模板。

## 运行配置

PMMS 3.0 使用 Qt `QSettings` 保存桌面端配置：

- 登录窗口保存服务器地址和请求超时。
- 设置页维护本地工作流默认值和库存导出文件名前缀。
- Windows 上由 Qt 使用平台原生 QSettings 后端保存这些值。

不要把真实密码、token、客户 IP 或客户数据写入已跟踪文件或打包文档。

## 交付检查清单

- 在 Windows 上使用与开发一致的 Python 主次版本构建。
- 确认 `dist/PMMS.exe` 或 `dist/PMMS/PMMS.exe` 存在。
- 确认 `template/` 和 `static/` 已进入交付输出目录。
- 在没有源码目录的干净 Windows 机器上启动可执行文件。
- 需要远程物料库存时，使用后端账号登录验证。
- 验证离线 `admin` 登录仍会禁用远程库存动作。
- 验证板材物料库存分页刷新、筛选和库存编码定位。
- 验证物料规格新增/编辑，以及被库存引用规格的后端保护提示。
- 验证库存入库和扣减 / 领用动作，不用普通编辑替代数量变化。
- 验证 XLSX 导入预览、确认导入、选中库存导出，以及默认文件名为
  `<name>-YYYYMMDD-HHMMSS.xlsx`。
- 验证管理员账号可进入用户管理页并创建、编辑、禁用用户。
- 使用小型 BOM 和 SolidWorks 工程图执行一次转换。
- 验证 DXF 分类、标注、合并输出目录。

## 常见故障

### 缺少 PyInstaller

执行：

```bash
uv sync
```

然后重新运行：

```bash
uv run python build.py
```

### SolidWorks COM 失败

检查：

- SolidWorks 已安装并授权。
- 当前 Windows 用户权限允许 COM 自动化。
- 同一 Windows 账号可以正常打开 SolidWorks。
- 发布包不是在 macOS 或 Linux 上构建的。

### 运行时报缺失模块

使用调试构建：

```bash
uv run python build.py --onedir --console
```

查看控制台错误，只把明确缺失的模块补到 `build.py` 的 `hidden_imports()` 中。

### 资源路径问题

确认 `template/` 和 `static/` 位于 `dist/` 中的可执行文件旁边。打包应用不能依赖
源码目录当前工作目录。

## 后续打包维护规则

- `BUILD.md` 和 `BUILD.zh-CN.md` 必须同步维护。
- `main.py` 保持为生产和打包入口。
- 不要把 `src/` 下的历史 demo 当作交付应用打包。
- 打包脚本不要自动改写 `requirements.txt`、`pyproject.toml` 或生成文档。
