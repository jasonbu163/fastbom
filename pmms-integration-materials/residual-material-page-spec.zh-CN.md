# Qt 余料管理页面规格

## 页面定位

新增一个独立一级页面，建议名称：

```text
余料管理
```

建议文件：

```text
gui/pages/residual_material_page.py
services/remote_api.py
```

如果项目决定先做通用远程表单页，也可以先使用：

```text
gui/pages/remote_form_page.py
```

但首版 UI 不建议做成泛接口调试器。页面应直接围绕余料台账操作员工作流。

## 页面结构

建议分为四块：

1. 顶部连接状态区。
2. 筛选区。
3. 余料库存表格。
4. 新增 / 编辑抽屉或弹窗。

### 连接状态区

显示：

- 后端 API URL。
- 当前登录用户。
- 登录状态。
- 最近一次请求状态。

动作：

- 登录。
- 退出。
- 刷新列表。

### 筛选区

字段：

- 材质：`materialGrade`。
- 厚度：`thickness`。
- 状态：`status`。
- 是否可复用：`reusable`。
- 最小宽度：`minWidth`。
- 最小长度：`minLength`。

默认筛选：

```text
inventoryType = leftover
status = available
```

### 表格列

推荐列：

- ID：`id`。
- 材质：`materialGrade`。
- 厚度：`thickness`。
- 宽：`width`。
- 长：`length`。
- 数量：`quantity`。
- 来源：`source`。
- 库位：`location`。
- 状态：`status` 显示中文。
- 可复用：`reusable` 显示“是 / 否”。
- 操作：编辑、作废。

首版可以不做分页；如果现场数据量变大，再推动后端分页接口。

### 新增 / 编辑表单

字段：

- 材质：选择 `materialId`，显示 `materialGrade + thickness`。
- 类型：固定 `leftover`，首版隐藏或只读。
- 宽：`width`。
- 长：`length`。
- 厚度：`thickness`，默认从材质带出，但允许核对。
- 数量：`quantity`，默认 `1`。
- 来源：`source`，默认 `manual-entry`。
- 库位：`location`。
- 状态：`status`，新增默认 `available`。
- 可复用：`reusable`，默认 `true`。

校验建议：

- `materialId` 必填。
- `width > 0`。
- `length > 0`。
- `thickness > 0`。
- `quantity >= 1`。
- 作废动作需要二次确认。

## Service 边界

`services/remote_api.py` 建议提供面向业务的方法：

```python
login(username: str, password: str) -> TokenSession
get_current_user() -> User
list_materials(enabled: bool | None = True) -> list[Material]
create_material(payload: MaterialCreate) -> Material
list_inventory_items(query: InventoryQuery) -> list[InventoryItem]
create_inventory_item(payload: InventoryCreate) -> InventoryItem
update_inventory_item(item_id: int, payload: InventoryUpdate) -> InventoryItem
void_inventory_item(item_id: int) -> InventoryItem
```

UI 页面不直接使用 `requests` / `httpx` 拼接接口。

## 线程 / UI 响应

远程请求不能阻塞 UI 线程。

可选方案：

- 复用现有 worker thread 风格。
- 新增轻量 API worker。
- 使用 Qt 的异步网络能力。

无论选哪种，页面需要显示：

- loading 状态。
- 成功摘要。
- 失败原因。
- 登录失效提示。

## 状态中文显示

建议映射：

```text
available -> 可用
reserved -> 已占用
consumed -> 已消耗
scrapped -> 已报废
voided -> 已作废
whole_sheet -> 整板
leftover -> 余料
```

注意：业务判断只使用英文 key。

## 最小验收

- 可以配置后端 API URL。
- 可以登录并保存本次会话 token，重启后不要求保持登录。
- 可以拉取材质列表。
- 可以新增材质。
- 可以拉取余料列表。
- 可以新增一条余料。
- 可以编辑余料库位 / 状态 / 可复用标记。
- 可以作废余料。
- 401 会提示重新登录。
- 网络断开或超时不会卡死界面。
- 不提交真实账号、密码或 token。

