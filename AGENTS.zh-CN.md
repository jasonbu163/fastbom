# AGENTS.zh-CN.md

FastBOM 是一个带有 AIIS 风味的本地桌面应用。应把它视为一个
PySide6 操作台，用于 BOM 驱动的工程文件处理、SolidWorks COM 自动化、
DXF 后处理、PMMS 板材物料库存和后端用户管理。

## 项目形态

- 交付形态：Qt / PySide6 桌面软件，不是 Web 应用。
- 当前入口：`main.py`。
- 当前生产 UI 路径：`gui/main_window.py` + `gui/worker_thread.py`。
- 当前本地业务核心：`core/bom_classifier.py`、`core/sw_converter.py`、
  `core/dxf_processor.py`。
- 本地 BOM、SolidWorks、DXF 核心代码已经调试过；第一阶段配置升级时应视为稳定代码。
- 资源真相源：SolidWorks 模板在 `template/`；图标等静态资源在 `static/`。
- 历史/demo 代码：`src/demo*.py`、`gui/gui.py` 和旧辅助脚本只作为参考材料，
  除非用户明确要求恢复或复用它们。

## 本仓库的 AIIS 原则

- 保持人类操作员的最终控制权。批量转换、文件写入、文件夹删除、
  SolidWorks COM 调用和远程提交都必须是明确的 UI 动作，并有清晰状态反馈。
- 让系统承载流程复杂性。优先提供稳定设置、默认值、校验和日志，而不是让操作员记住隐藏规则。
- 分离操作台和副作用。UI 控件只收集意图；worker/service 代码执行耗时本地任务和远程请求。
- 把文件和 API 响应视为契约。当 typed helper、service 或 settings object 才是真边界时，
  不要在 UI 里临时发明字段映射。
- 保持 AIIS 工程 grounding。改动应能落回 PySide6 控件、worker 线程、
  SolidWorks COM 生命周期、DXF 文件、QSettings、API payload、日志或 PyInstaller 打包。

## 工程边界

- `main.py` 应保持轻量：创建 `QApplication`、加载设置/主题、创建主窗口、启动事件循环。
- `gui/` 负责控件、页面组合、信号和展示状态。
- `gui/worker_thread.py` 负责本地长耗时任务的后台执行衔接。不要在 UI 线程里执行
  pandas、SolidWorks、DXF、文件系统或 HTTP 耗时工作。
- `core/` 负责确定性的本地处理逻辑，以及 SolidWorks/DXF 行为。
- 设置升级阶段不要重写本地核心业务逻辑；只有在必须把设置注入现有行为时，才做小范围兼容改动。
- 远程 PMMS API 代码应放在 `MainWindow` 外部，优先使用小型 service/client 模块，
  例如 `services/remote_api.py`。
- 设置/配置代码放在 `config/settings.py`。
- 项目级工具放在 `tools/`；不要让工具脚本悄悄依赖 GUI 状态。

## UI 演进规则

- 引入新的业务页面后，不要继续给 `MainWindow` 追加更多纵向“步骤”。
- 多工作流场景优先使用侧边栏 + `QStackedWidget` 页面模型：
  本地处理、板材物料库存、用户管理、设置应拆成独立页面。
- 当前本地处理流程位于 `gui/pages/local_processing_page.py`，并由 `MainWindow`
  中的页面栈承载。
- 新增页面模块应小而清晰，并按工作流命名，例如
  `gui/pages/residual_material_page.py`、`gui/pages/user_management_page.py`、
  `gui/pages/settings_page.py`。
- 新增一级页面或本地处理子页面时，遵循 `docs/qt-navigation.zh-CN.md`。
- 长耗时本地工作流页面应保持日志可见，提供显式“保存日志”动作，并且只在操作员
  显式点击时打开输出目录。
- UI 文案应面向操作员、务实清楚。避免在应用内写营销式表达。
- 远程 PMMS 页面必须展示请求状态、响应摘要和错误反馈，并且不能冻结 UI。

## 配置规则

- 桌面端运行设置应通过 Qt 标准机制 `QSettings` 保存。不要为 Qt 客户端新增
  后端式环境配置层。
- 推荐优先级：内置默认值 < QSettings 用户持久化设置 < 当前表单输入。
- 适合配置化的内容包括：后端 API base URL、请求超时、默认 BOM 列、主题名、
  模板目录、输出目录名、SolidWorks 是否可见、DXF 标注参数。
- 不要为了一次性值增加配置项；只有支持真实现场交付或重复操作员使用时，才配置化。

## 远程 API 契约规则

- API URL、超时和认证相关值不能硬编码在页面里。
- GET / POST / PATCH / DELETE payload 构造应放在 service/client 边界。UI 不应
  内联拼接 URL，也不应直接序列化业务 payload。
- 如果本项目控制服务端契约，遵循 AIIS 响应结构：
  `{"code": 200, "message": "success", "data": ...}`。
- 如果远程服务器使用不同契约，应在 service 模块和 README 中记录期望的请求/响应结构。
- 实现或调整远程 PMMS 页面/API client 前，必须先读取
  `pmms-integration-materials/` 中的后端契约材料。
- 正常登录凭据必须来自后端 API。
- 兜底 `admin` 登录只允许保存在本机 Qt 设置中，用于诊断或启动兜底。不要把
  兜底凭据写入已跟踪文件或日志。
- 后端的保底最高权限账号不是这个 `admin` 账号。
- 如果 Qt 客户端使用兜底 `admin` 强制登录，本次会话必须禁用远程库存和用户管理工作流。
- 桌面应用内不要维护长期 mock API。只有真实接口暂不可用时，才允许短期静态样例推进 UI。

## 验证

项目命令必须使用项目运行环境。本仓库使用 `uv` 和 Python 3.13。

文档类改动后的最小检查：

```bash
uv run python -m compileall main.py config core gui utils build.py
```

如果改动 UI 或 worker，还需要在具备 GUI 运行条件的机器上启动应用：

```bash
uv run python main.py
```

如果改动 SolidWorks 转换逻辑，需要在安装了 SolidWorks 的 Windows 机器上验证。
不要在 macOS 或没有 SolidWorks 的机器上声称完整转换链路已验证。

如果改动打包逻辑，优先运行：

```bash
uv run python build.py
```

如果因为主机缺少 Windows、SolidWorks、COM 或 GUI 支持而无法运行某个命令，
最终报告里必须明确说明。

## 文档规则

- `README.md` 和 `README.zh-CN.md` 必须与真实入口、运行环境、目录结构和交付形态保持一致。
- 如果项目从单页工作流演进为侧边栏/页面栈，必须同步更新 README 和本文件。
- 如果本地桌面模式具备跨 AIIS 项目复用价值，可以建议提炼 Qt/PySide6 桌面端 skill，
  但除非用户明确要求，不要直接创建共享 skill。
