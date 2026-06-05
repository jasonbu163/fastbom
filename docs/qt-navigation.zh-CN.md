# Qt 导航说明

FastBOM 使用两级导航：

- `gui/main_window.py` 中的一级导航，用于顶层工作流。
- 工作流页面内部的二级导航，用于拆分该工作流下的操作阶段。

导航代码只负责页面组织。不要把 BOM、SolidWorks、DXF 或远程 API 业务逻辑写进导航控件。

## 新增一级页面

新增远程表单提交这类顶层工作流时，使用一级页面。

1. 在 `gui/pages/` 下创建页面组件，例如 `gui/pages/remote_form_page.py`。
2. 在 `gui/main_window.py` 中导入页面。
3. 给 `self.sidebar` 增加一个条目。
4. 按相同顺序把页面组件加入 `self.pages`。
5. 保留 `self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)`。

示例：

```python
from gui.pages.remote_form_page import RemoteFormPage

self.sidebar.addItem("远程表单")
self.remote_form_page = RemoteFormPage(settings=self.settings)
self.pages.addWidget(self.remote_form_page)
```

顺序必须对应：

```text
sidebar row 0 -> pages index 0
sidebar row 1 -> pages index 1
sidebar row 2 -> pages index 2
```

## 新增本地处理子页面

在本地处理工作流下新增一个阶段时，使用二级页面。

1. 给 `LocalProcessingPage.local_nav` 增加一个条目。
2. 按相同顺序给 `LocalProcessingPage.local_pages` 增加一个页面。
3. 新增一个小的 `_create_*_page()` 方法，返回 `QWidget`。
4. worker 和副作用逻辑放在 `LocalProcessingPage` 方法或 `gui/worker_thread.py` 中，
   不要写进导航控件。

示例：

```python
self.local_nav.addItem("质量复核")
self.local_pages.addWidget(self._create_quality_review_page())

def _create_quality_review_page(self) -> QWidget:
    page, layout = self._page_shell()
    self._create_quality_review_step(layout)
    layout.addStretch()
    return page
```

当前本地处理映射：

```text
准备与识别 -> 第一步 + 第二步
分类转换   -> 第三步
DXF 标注   -> 第四步
DXF 合并   -> 第五步
```

## 长耗时子页面模式

如果某个子页面只承载一个长耗时任务，应让任务卡片填满可用高度：

```python
def _create_dxf_mark_page(self) -> QWidget:
    page, layout = self._page_shell()
    self._create_step4(layout, expand=True)
    return page
```

在步骤内部，日志控件应带 stretch 加入布局，让它吸收多余垂直空间：

```python
group_layout.addWidget(self.log2, 1)
layout.addWidget(group, 1)
```

需要填满内容区的单任务页面，不要在末尾再添加 `layout.addStretch()`。

长耗时任务页应保持日志可见，并在日志下方提供显式操作：

- `保存当前日志`：将当前可见日志保存到用户选择的文件。
- `打开所在目录`：任务成功后，由操作员手动打开输出目录。

不要在 worker 完成回调中自动打开输出目录。这个副作用应由操作员显式触发。

## 布局规则

一级侧边栏和内容卡片是 `MainWindow` 中的同级区域。它们应使用相同外边距，
让侧边栏看起来是一张导航卡片，而不是铺满窗口高度的轨道。

二级导航属于内容卡片内部，因为它描述的是当前一级工作流中的阶段，而不是全局应用区域。
