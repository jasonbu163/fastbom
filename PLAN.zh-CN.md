# FastBOM 通用化演进计划

> 本计划与 `PLAN.md` 双语同步。项目方向变化时，两个文件应保持一致。

**目标：** 将 FastBOM 从一个已经跑通的单工作流桌面工具，演进为更通用的
AIIS 风格本地桌面应用：具备可配置 Qt 设置、清晰页面边界，并为未来远程 API
表单能力打好基础。

**判断：** 第一阶段先做 Qt 应用设置是合理的。它能先减少硬编码假设，
给未来远程 API 页面提供稳定配置来源，而且初始改动足够小，不需要立刻触碰
SolidWorks 转换主链路。

## 当前基线

- 入口：`main.py`。
- 当前 UI：`gui/main_window.py` 中的 PySide6 纵向单页工作流。
- 当前本地 worker 边界：`gui/worker_thread.py`。
- 当前业务核心：`core/bom_classifier.py`、`core/sw_converter.py`、
  `core/dxf_processor.py`。
- 当前硬编码内容包括主题、默认 BOM 列、输出目录名、模板路径、
  SolidWorks 是否可见、DXF 标注参数等。
- 本地 BOM、SolidWorks、DXF 业务代码已经调试过；第一阶段通用化时应视为稳定代码。
- 完整转换验证依赖 Windows + SolidWorks；macOS 只能验证文档、语法和纯 Python 结构。

## 目标架构

```text
main.py
  加载设置/主题
  创建 MainWindow

config/
  settings.py              # 默认值和 QSettings 衔接

gui/
  main_window.py           # 侧边栏/页面外壳
  pages/
    remote_form_page.py
    settings_page.py

services/
  remote_api.py            # 未来 GET/POST 客户端

core/
  bom_classifier.py
  sw_converter.py
  dxf_processor.py
```

后续应让 `MainWindow` 保持轻量。UI 页面收集操作员意图；config 和 service 模块
负责运行设置和外部契约；worker/core 模块执行本地长耗时副作用。

## 第一阶段：配置与设置底座

**目的：** 在不改变现有操作流程、不新增远程 API 页的前提下，让应用先具备配置能力。

**范围：**

- 新增设置模块，包含内置默认值，并通过 `QSettings` 保存用户设置。
- 把最安全的一批硬编码值迁入设置层：
  - 应用主题；
  - 默认 BOM 零件/材料/数量列名；
  - 输出目录名；
  - 模板目录；
  - SolidWorks 是否可见；
  - DXF 文字图层、颜色、默认高度、间距；
  - 未来后端 API base URL 和请求超时；
  - 本机 Qt 设置中的兜底 admin 用户名和密码。
- 避免改动本地核心业务算法。只有为了保持现有行为并接入设置层时，才对 `core/`
  做小范围配置注入改动。
- 如果不需要重构整个窗口，可以加一个最小设置 UI；否则先暴露设置模块，
  把完整设置页放到第二阶段。
- 设置契约落地后，同步 README 和 AGENTS 文件。

**建议文件：**

- 新增：`config/__init__.py`。
- 新增：`config/settings.py`。
- 修改：`main.py`。
- 修改：`gui/main_window.py`。
- 修改：`gui/worker_thread.py`。
- 仅在设置注入需要时修改：`core/bom_classifier.py`。
- 仅在设置注入需要时修改：`core/sw_converter.py`。
- 仅在设置注入需要时修改：`core/dxf_processor.py`。
- 修改：`README.md`。
- 修改：`README.zh-CN.md`。
- 修改：`AGENTS.md`。
- 修改：`AGENTS.zh-CN.md`。

**设置优先级：**

```text
内置默认值 < QSettings 持久化值 < 当前表单输入
```

**验收标准：**

- `main.py` 不再直接硬编码主题。
- 默认 BOM 列名从设置层读取。
- 输出目录名从设置层读取。
- `SWConverter` 可以使用配置化模板目录和 SolidWorks 可见性开关。
- `DXFProcessor` 可以使用配置化标注参数，默认设置下行为保持不变。
- 空 QSettings 时，应用仍保持当前默认行为。
- 使用默认设置时，完整 SolidWorks 转换行为保持不变。

**验证：**

```bash
uv run python -m compileall main.py config core gui utils build.py
```

在 macOS 上，`uv run` 可能会因为 `pywin32` 只支持 Windows 而提前失败。
这种情况下，使用只读语法检查，并明确说明平台限制：

```bash
python3 -c "from pathlib import Path; paths=[Path('main.py'),Path('build.py'),*Path('config').glob('*.py'),*Path('core').glob('*.py'),*Path('gui').glob('*.py'),*Path('utils').glob('*.py')]; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in paths]; print(f'compiled {len(paths)} files')"
```

在安装了 SolidWorks 的 Windows 机器上：

```bash
uv run python main.py
```

然后用一组小型 BOM + `.SLDDRW` 样例验证现有本地流程。

## 第二阶段：桌面导航与设置页

**状态：** 当前桌面外壳核心形态已落地。`MainWindow` 负责一级侧边栏和页面栈；
本地处理流程位于 `gui/pages/local_processing_page.py`，并带有二级导航。

**目的：** 从单一纵向工作流演进为能承载多个工作流的桌面应用外壳。

**范围：**

- 引入侧边栏 + `QStackedWidget`。
- 将本地处理流程作为首个页面承载。
- 将本地处理拆成准备与识别、分类转换、DXF 标注、DXF 合并四个二级页面。
- 新增由第一阶段设置模块驱动的设置页。
- 保持当前本地处理核心行为不变。

**建议文件：**

- 新增：`gui/pages/__init__.py`。
- 新增：`gui/pages/local_processing_page.py`。
- 新增：`gui/pages/settings_page.py`。
- 修改：`gui/main_window.py`。
- 修改：`main.py`。
- 新增：`docs/qt-navigation.zh-CN.md`。

**验收标准：**

- 首屏仍然展示本地处理工作流。
- 本地处理子页面可以通过二级导航进入。
- 长耗时任务页提供保存日志和打开输出目录的显式动作。
- 设置可以在 UI 中查看和保存。
- 保存设置通过 `QSettings` 写入。
- 执行现有 worker 任务时 UI 仍保持响应。

## 第三阶段：远程 API 表单页

**目的：** 在设置和导航稳定后，新增远程 GET/POST 表单工作流。

**范围：**

- 实现页面和客户端前，先读取后端 `openapi.json`。
- 新增远程表单页面。
- 新增 HTTP service/client 边界。
- 使用配置化后端 API base URL 和超时。
- 新增普通用户的后端认证登录流程。
- 只允许从本机 Qt 设置使用兜底 `admin` 登录。
- 记录后端的保底最高权限账号不是这个 `admin` 账号。
- 如果客户端会话使用兜底 `admin` 强制登录，必须禁用远程表单工作流。
- 在 UI 中展示请求状态、响应摘要和错误反馈。
- 静态样例只能短期存在，真实接口接入后应清理。

**建议文件：**

- 新增：`services/__init__.py`。
- 新增：`services/remote_api.py`。
- 新增：`gui/pages/remote_form_page.py`。
- 修改：`gui/main_window.py`。
- 修改：`config/settings.py`。

**验收标准：**

- GET 和 POST 操作不阻塞 UI。
- URL 和超时不硬编码在页面里。
- 普通登录凭据通过后端 API 契约获取。
- 兜底 admin 凭据不能出现在已跟踪文件、日志或 UI 展示中。
- 兜底 admin 会话下禁用远程表单。
- service 模块负责请求构造和响应解析。
- README 记录远程请求和响应结构。

## 第四阶段：AIIS 桌面端 Skill 候选

**目的：** 判断本项目是否已经有足够证据，可以提炼可复用的 AIIS Qt/PySide6
本地桌面端 skill。

**需要收集的证据：**

- 设置层同时支撑本地处理页和远程 API 页。
- 侧边栏/页面模型支撑至少两个工作流。
- worker 侧本地副作用仍与 UI 分离。
- 打包和平台限制已被文档化。

**可能的 skill 边界：**

- PySide6 桌面外壳结构。
- QSettings 优先级。
- 本地副作用的 worker 线程规则。
- 远程 API service 边界。
- PyInstaller 资源和平台检查。

除非用户明确要求，不直接创建共享 skill。

## 阶段门

- **Gate 1：** 空 QSettings 时设置默认值可工作。
- **Gate 2：** QSettings 持久化设置已文档化。
- **Gate 3：** 现有本地流程在 Windows + SolidWorks 上仍可用。
- **Gate 4：** 侧边栏/页面拆分后首屏仍有真实工作面。
- **Gate 5：** 远程 API 页面使用设置/service 边界。
- **Gate 6：** 可复用桌面端规则有足够证据进入未来 skill。
