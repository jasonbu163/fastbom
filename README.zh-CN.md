# FastBOM

FastBOM 是一个 PySide6 本地桌面应用，用于制造业工程文件处理流程。它可以读取
BOM 表，匹配 SolidWorks 工程图文件，通过 SolidWorks COM 自动化转换 DXF，
再按材质和厚度分类、标注、合并 DXF 文件，方便后续生产和下游处理。

当前项目是本地桌面操作台，不是 Web 应用。`src/` 下的 NiceGUI/demo 文件保留为
历史参考；当前真实入口是 `main.py`。

## 当前工作流

首屏是侧边栏桌面外壳中的本地处理页；设置页也可以从侧边栏进入。

1. 选择包含 BOM 表和 `.SLDDRW` 工程图的项目目录。
2. 自动识别 BOM 文件和表头。
3. 匹配 SolidWorks 工程图，转换 DXF，并输出到 `result/1_分类结果`。
4. 对 DXF 添加文件名标注，并输出到 `result/2_DXF处理结果`。
5. 按材质和厚度合并 DXF，并输出到 `result/3_合并文件`。

## 核心能力

- 智能识别 BOM 表头，支持表头不在第一行的情况。
- 解析 `A3板 T=10`、`A3板T=10` 这类材质和厚度字段。
- 根据 BOM 零件名和 SolidWorks 工程图文件名做模糊匹配。
- 使用后台线程执行耗时任务，避免 Qt 界面卡死。
- 通过 SolidWorks COM 自动化替换模板、设置视图比例、导出 DXF。
- 使用 `ezdxf` 做 DXF 标注和按材质/厚度合并。
- 支持通过 PyInstaller 打包为 Windows 可执行程序。

## 技术栈

- Python 3.13，使用 `uv` 管理项目环境。
- PySide6 作为桌面 UI 框架。
- `qt-material` 作为当前主题方案。
- `pandas`、`openpyxl`、`xlrd` 用于 BOM 表处理。
- `pywin32`、`pythoncom` 用于 Windows 上的 SolidWorks COM 集成。
- `ezdxf` 用于 DXF 文件处理。
- PyInstaller 用于可执行文件打包。

## 项目结构

```text
fastbom/
├── main.py                 # PySide6 应用入口
├── core/                   # 本地处理、SolidWorks、DXF 业务逻辑
│   ├── bom_classifier.py
│   ├── dxf_processor.py
│   ├── sw_converter.py
│   ├── file_export.py
│   ├── set_template.py
│   └── set_views.py
├── config/                 # 运行默认值和 QSettings 衔接
│   └── settings.py
├── gui/                    # 桌面界面和后台线程衔接
│   ├── main_window.py
│   ├── pages/
│   │   └── settings_page.py
│   ├── worker_thread.py
│   └── gui.py              # 历史/参考 UI 路径
├── utils/                  # 日志、提示框、COM 辅助工具
├── template/               # SolidWorks 图纸模板和制图标准
├── static/                 # 图标等静态资源
├── tools/                  # 项目辅助脚本和历史运行器
├── src/                    # 历史 NiceGUI/demo 实验代码
├── build.py                # PyInstaller 打包辅助脚本
├── BUILD.md                # 打包说明
├── pyproject.toml
└── uv.lock
```

## 本地运行

使用项目运行环境安装依赖：

```bash
uv sync
```

启动桌面应用：

```bash
uv run python main.py
```

SolidWorks 转换链路需要 Windows 且已安装 SolidWorks。可以在其他系统上查看界面
和纯 Python 模块，但不能完整验证 COM 转换流程。

## 轻量验证

文档或结构调整后：

```bash
uv run python -m compileall main.py config core gui utils build.py
```

如果改了 GUI，还需要启动应用：

```bash
uv run python main.py
```

如果改了打包逻辑：

```bash
uv run python build.py
```

## 配置

FastBOM 现在已经在 `config/settings.py` 中建立独立设置层。它保留当前本地工作流
默认值，同时允许 UI 设置通过 Qt 标准设置机制覆盖部分配置。

- 使用 `QSettings` 保存桌面应用设置。
- Qt 会选择平台原生后端：Windows 注册表、macOS plist、Linux 上常见的 ini/config
  风格文件。
- 登录窗口负责配置后端 API 地址和请求超时，因为这些值在主窗口打开前就会用于认证。
- 设置页用于配置本地工作流默认值，例如默认 BOM 列、模板目录、输出目录、
  DXF 参数、SolidWorks 可见性，以及离线 `admin` 密码。
- 离线账号用户名固定为 `admin`，不能在 UI 中修改；只有本地密码可以通过
  `QSettings` 覆盖，不写入已跟踪文件或日志。

推荐优先级：

```text
内置默认值 < QSettings 用户持久化设置 < 当前表单输入
```

## 远程 API 认证方向

远程 API 集成会在后端 `openapi.json` 提供后实现。Qt 客户端应遵循后端契约，
不要在本地自行发明请求或响应结构。

认证规则：

- 正常登录账号从后端 API 获取。
- `admin` 离线账号只允许作为本机 Qt 设置中的应急/默认登录来源。
- 离线 `admin` 密码可以由桌面客户端保存到 `QSettings`，但不能写入已跟踪文件或日志。
- 后端的保底最高权限账号不是这个 `admin` 账号。
- 如果 Qt 客户端使用离线 `admin` 身份登录，本次会话必须禁用远程表单功能。
- 只有正常后端认证通过的用户会话，才允许使用远程 GET/POST 表单工作流。
- 如果使用后端账号登录，主窗口关闭时客户端应使用当前 refresh token 调用后端
  logout；离线 `admin` 会话不调用后端 logout。
- 如果忘记离线密码，不需要重新编译软件。可以用后端非 admin 账号登录后在设置页
  重新设置离线密码；如果没有可用后端账号，则清理本机 `QSettings` 中的离线密码键，
  让客户端回到内置默认值。

### 离线 admin 密码重置

离线账号的设计应保持简单，并且只服务于本机进入软件：

- 用户名永远是 `admin`，UI 中不能修改。
- 内置默认密码是 `#456@admin`。
- 设置页只在输入新密码时覆盖本机离线密码；密码框留空则保留当前密码。
- 使用离线 `admin` 登录可以进入桌面软件，但会禁用远程物料库功能。

重置路径：

- 如果还记得当前离线密码，用 `admin` 登录，进入设置页，填写新的离线密码并保存。
- 如果忘记离线密码，但还有后端非 admin 账号可用，用后端账号登录，进入设置页，
  填写新的离线密码并保存。
- 如果离线登录和后端登录都不可用，清理本机 `QSettings` 中的
  `auth.fallback_admin_password` 键。下次启动时，客户端会回到内置默认密码
  `#456@admin`。不需要重新编译软件。

## 本地核心稳定性

本地 BOM、SolidWorks、DXF 处理代码已经调试过，并且在目标环境中可以运行。
第一阶段通用化改造应避免改动核心业务算法；除非为了接入设置层需要非常小的兼容性
改动，否则优先在现有行为外层增加配置能力，不重写本地处理逻辑。

## UI 结构

当前 `gui/main_window.py` 已经使用一级侧边栏卡片 + 内容卡片 + 页面栈：

- 本地处理页，内部包含准备与识别、分类转换、DXF 标注、DXF 合并四个二级页面。
- 设置页。

远程 API 表单页会在后端 `openapi.json` 提供后再新增。

导航扩展规则见 `docs/qt-navigation.zh-CN.md`。

HTTP 请求构造、响应解析和错误处理应放到独立 service/client 边界中，不要直接堆在
主窗口类里。

## AIIS 说明

FastBOM 很适合作为 AIIS 本地桌面软件规范的样本：PySide6 界面、后台线程副作用、
SolidWorks COM 生命周期、文件系统契约、用户设置、远程 API 提交和 PyInstaller
打包都集中在一个具体项目里。

项目级 Agent 规则见 `AGENTS.md`。
