# Qt Navigation Guide

FastBOM uses two navigation levels:

- Primary navigation in `gui/main_window.py` for top-level workflows.
- Secondary navigation inside a workflow page when that workflow has multiple
  operational stages.

Keep navigation code in UI modules only. Do not move BOM, SolidWorks, DXF, or
remote API business logic into navigation widgets.

## Add A Primary Page

Use this when adding a top-level workflow such as remote form submission.

1. Create a page widget under `gui/pages/`, for example
   `gui/pages/remote_form_page.py`.
2. Import the page in `gui/main_window.py`.
3. Add one item to `self.sidebar`.
4. Add the page widget to `self.pages` in the same order.
5. Keep `self.sidebar.currentRowChanged.connect(self.pages.setCurrentIndex)`.

Example:

```python
from gui.pages.remote_form_page import RemoteFormPage

self.sidebar.addItem("远程表单")
self.remote_form_page = RemoteFormPage(settings=self.settings)
self.pages.addWidget(self.remote_form_page)
```

The order must match:

```text
sidebar row 0 -> pages index 0
sidebar row 1 -> pages index 1
sidebar row 2 -> pages index 2
```

## Add A Local Processing Subpage

Use this when adding a new stage under the local processing workflow.

1. Add one item to `LocalProcessingPage.local_nav`.
2. Add one widget to `LocalProcessingPage.local_pages` in the same order.
3. Create a small `_create_*_page()` method that returns a `QWidget`.
4. Keep worker and side-effect logic in methods on `LocalProcessingPage` or in
   `gui/worker_thread.py`, not in the navigation widget.

Example:

```python
self.local_nav.addItem("质量复核")
self.local_pages.addWidget(self._create_quality_review_page())

def _create_quality_review_page(self) -> QWidget:
    page, layout = self._page_shell()
    self._create_quality_review_step(layout)
    layout.addStretch()
    return page
```

The local processing mapping is currently:

```text
准备与识别 -> Step 1 + Step 2
分类转换   -> Step 3
DXF 标注   -> Step 4
DXF 合并   -> Step 5
```

## Long-Running Subpage Pattern

For a subpage that contains one long-running task, let the task card fill the
available height:

```python
def _create_dxf_mark_page(self) -> QWidget:
    page, layout = self._page_shell()
    self._create_step4(layout, expand=True)
    return page
```

Inside the step, add the log widget with stretch so it absorbs spare vertical
space:

```python
group_layout.addWidget(self.log2, 1)
layout.addWidget(group, 1)
```

Do not add a trailing `layout.addStretch()` on single-task pages that should
fill the content area.

Long-running task pages should keep the log visible and place explicit actions
below it:

- `保存当前日志` saves the current visible log to a user-selected file.
- `打开所在目录` opens the output directory after a successful run.

Do not automatically open output folders from worker completion callbacks. The
operator should trigger that side effect manually.

## Layout Rule

The primary sidebar and the content card are siblings in `MainWindow`. They
should share the same outer margins so the sidebar reads as a navigation card,
not as a full-window rail.

The secondary navigation belongs inside the content card because it describes
sections of the current primary workflow, not global application areas.
