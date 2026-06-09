# PMMS 后端 API 契约

本文只记录 Qt 板材物料库存管理首版需要消费的后端契约。以后如果后端
`/openapi.json` 与本文冲突，以实际 `openapi.json` 为准，并同步更新本目录。

## 基础规则

- Base URL 来自 Qt 设置，不在页面或 service 中硬编码。
- API 前缀：`/api/v1`。
- 请求和响应字段使用 `camelCase`。
- Qt 页面不做全局 `snake_case` / `camelCase` 转换。
- HTTP 请求放在 `services/remote_api.py`。
- UI 页面只调用 service 方法，不直接拼 URL 或解析原始响应。
- 普通登录走后端 `/auth/login`。
- 不把真实密码、token、兜底账号写入 Git 跟踪文件、日志或截图。
- 当前 PMMS 后端和 SQL Server 统一使用 `Asia/Shanghai` 中国现场本地时间。
- API 返回的 `createdAt` / `updatedAt` 等时间字段按现场本地时间展示，Qt 首版不要再按用户时区二次换算。
- Qt 可以只做显示格式化，例如 `YYYY-MM-DD HH:mm:ss`；不要把这些字段当 UTC 转换。

## 响应信封

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

业务失败响应：

```json
{
  "code": 400,
  "message": "business_error",
  "data": null,
  "errorCode": "stable_error_key"
}
```

Qt 判断逻辑建议：

- 网络错误：显示“无法连接后端 / 请求超时”。
- HTTP 401：清理当前 token，提示重新登录。
- HTTP 403：提示权限不足。
- HTTP 200 且 `code == 200`：按 `data` 渲染。
- HTTP 200 且 `code != 200`：按 `errorCode` 显示业务错误。
- HTTP 4xx/5xx：显示状态码和响应摘要，避免吞错。

## 分页结构

数据会持续增长的列表必须优先使用分页接口。老的全量列表接口仅保留给小数据量、
兼容或下拉选项场景。

统一查询参数：

```text
page
pageSize
```

统一响应 `data`：

```json
{
  "items": [],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 0
  }
}
```

Qt 页面判断：

- `items` 渲染当前页。
- `meta.total` 渲染总数。
- `meta.page` 和 `meta.pageSize` 作为分页控件当前状态。
- 默认 `page=1`、`pageSize=20`。
- 当前后端会把 `pageSize` 归一到 `1..200`。

## 认证接口

### 登录

```text
POST /api/v1/auth/login
```

请求：

```json
{
  "username": "operator",
  "password": "password-from-user-input"
}
```

成功响应 `data`：

```json
{
  "accessToken": "access-token",
  "refreshToken": "refresh-token",
  "tokenType": "bearer"
}
```

后续请求头：

```text
Authorization: Bearer <accessToken>
```

## 用户管理接口

用户 CRUD 接口见 `user-management-api.zh-CN.md`。首版规则：

- root 可管理 `admin` / `operator` / `viewer`。
- admin 只能管理 `operator` / `viewer`。
- 普通账户只能修改自己的密码。
- Qt 端不要把“本地兜底 admin”当成后端 root。
- 删除用户是禁用账号，不是物理删除。
- 用户列表页面优先使用 `GET /api/v1/users/page`。

### 当前用户

```text
GET /api/v1/auth/me
```

成功响应 `data`：

```json
{
  "username": "operator",
  "displayName": "Operator",
  "role": "operator",
  "status": "active"
}
```

### 刷新 token

```text
POST /api/v1/auth/refresh
```

请求：

```json
{
  "refreshToken": "refresh-token"
}
```

### 退出登录

```text
POST /api/v1/auth/logout
```

请求：

```json
{
  "refreshToken": "refresh-token"
}
```

## 物料规格 / 材质主数据

`materials` 表示板材物料规格主数据。Qt 页面上建议显示为“物料规格”或“材质管理”，
不要新增一个一级侧边栏页面；从“板材物料库存管理”页的工具栏打开管理弹窗即可。

字段说明：

```json
{
  "id": 1,
  "materialGrade": "Q235",
  "thickness": 2.5,
  "specDescription": "冷轧板",
  "defaultUnit": "张",
  "enabled": true
}
```

- `materialGrade + thickness` 唯一。
- `enabled=false` 表示禁用，不从新增库存项的默认下拉选项中展示。
- 不提供删除接口；已使用过的规格应禁用，而不是物理删除。
- 如果材料已被库存项引用，后端不允许修改 `materialGrade` / `thickness`，避免历史库存含义改变。
- 已引用材料仍允许修改 `specDescription`、`defaultUnit`、`enabled`。

### 列表

```text
GET /api/v1/materials?enabled=true
```

成功响应 `data[]`：

```json
{
  "id": 1,
  "materialGrade": "Q235",
  "thickness": 2.5,
  "specDescription": "Laser cutting sheet",
  "defaultUnit": "sheet",
  "enabled": true
}
```

这个全量列表只适合新增库存项的下拉选项。物料规格管理弹窗应优先使用分页接口。

### 分页

```text
GET /api/v1/materials/page?page=1&pageSize=20&enabled=true&materialGrade=Q&thickness=2.5
```

支持查询参数：

```text
page
pageSize
enabled
materialGrade
thickness
```

成功响应 `data`：

```json
{
  "items": [
    {
      "id": 1,
      "materialGrade": "Q235",
      "thickness": 2.5,
      "specDescription": "冷轧板",
      "defaultUnit": "张",
      "enabled": true
    }
  ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 1
  }
}
```

### 详情

```text
GET /api/v1/materials/{materialId}
```

找不到返回业务错误：

```json
{
  "code": 400,
  "message": "material_not_found",
  "data": null,
  "errorCode": "material_not_found"
}
```

### 新增

```text
POST /api/v1/materials
```

请求：

```json
{
  "materialGrade": "Q235",
  "thickness": 2.5,
  "specDescription": "Laser cutting sheet",
  "defaultUnit": "sheet",
  "enabled": true
}
```

约束：

- `materialGrade + thickness` 唯一。
- 板材物料库存项新增前必须有对应 `materialId`。
- 重复规格返回 `material_already_exists`。
- Qt 新增库存项时应先做“选择已有规格”，旁边提供“+ 新增规格”快速入口。

### 更新 / 启用 / 禁用

```text
PATCH /api/v1/materials/{materialId}
```

请求可以只传变更字段：

```json
{
  "specDescription": "冷轧板",
  "defaultUnit": "张",
  "enabled": false
}
```

如果材料还没有被库存项引用，也可以修改关键规格：

```json
{
  "materialGrade": "Q235B",
  "thickness": 3.0
}
```

注意：

- 启用 / 禁用直接传 `enabled=true/false`，没有单独的 delete 接口。
- 如果已被库存项引用，再修改 `materialGrade` / `thickness` 会返回 `material_in_use`。
- 如果修改后与其他材料重复，会返回 `material_already_exists`。
- Qt 端不需要提前判断材料是否已被库存引用；普通编辑直接提交 `PATCH`，如果收到
  `material_in_use`，提示“该规格已用于库存，不能修改材质 / 牌号或厚度”。
- Qt 编辑弹窗可以始终展示 `materialGrade` / `thickness` 输入框；是否禁用由 UI 体验决定，
  但最终以后端返回为准。

## 板材物料库存

### 列表

```text
GET /api/v1/inventory-items
```

支持查询参数：

```text
materialId
inventoryCode
inventoryType
status
reusable
minWidth
minLength
materialGrade
thickness
```

筛选匹配规则：

- `inventoryCode`：模糊匹配，适合在主表搜索框输入编码片段。
- `materialGrade`：模糊匹配，适合输入部分材质 / 牌号。
- `materialId`、`inventoryType`、`status`、`reusable`、`thickness`：精确匹配。
- `minWidth`、`minLength`：下限范围匹配。

实现说明：

- `/inventory-items` 和 `/inventory-items/page` 的筛选参数由后端 API 层传给 service 层，再由 CRUD 层拼接 SQL。
- `materialGrade` 和 `inventoryCode` 的 `LIKE` 模糊匹配在后端 CRUD 层完成，Qt 端只需要按参数名传值，不要再做本地二次过滤。

库存列表常用查询：

```text
GET /api/v1/inventory-items?status=available
```

Qt 板材物料库存列表页面优先使用分页接口：

```text
GET /api/v1/inventory-items/page?status=available&page=1&pageSize=20
```

说明：

- 页面默认不限制 `inventoryType`，同时展示整板 / 整料和余料。
- 用户需要时再按 `inventoryType=whole_sheet` 或 `inventoryType=leftover` 筛选。
- 当前 XLSX 导入 / 导出字段和前端功能围绕板材类物料；管材、型材等字段后续单独规划。

成功响应 `data[]`：

```json
{
  "id": 10,
  "inventoryCode": "RM:Q235-1200x800x2.5-20260605-10",
  "materialId": 1,
  "materialGrade": "Q235",
  "inventoryType": "leftover",
  "width": 1200,
  "length": 800,
  "thickness": 2.5,
  "quantity": 1,
  "remark": "",
  "source": "manual-entry",
  "location": "A-01",
  "status": "available",
  "reusable": true,
  "createdAt": "2026-06-06T10:00:00",
  "updatedAt": "2026-06-06T10:00:00"
}
```

### 新增库存项

```text
POST /api/v1/inventory-items
```

请求：

```json
{
  "inventoryCode": null,
  "materialId": 1,
  "inventoryType": "leftover",
  "width": 1200,
  "length": 800,
  "thickness": 2.5,
  "quantity": 1,
  "remark": "",
  "source": "manual-entry",
  "location": "A-01",
  "status": "available",
  "reusable": true
}
```

### 更新库存项

```text
PATCH /api/v1/inventory-items/{inventoryItemId}
```

请求可以只传变更字段：

```json
{
  "remark": "manual review",
  "location": "B-02",
  "status": "reserved",
  "reusable": true
}
```

### 作废库存项

```text
POST /api/v1/inventory-items/{inventoryItemId}/void
```

成功后 `status == "voided"`。

### 按库存编码定位

库存编码使用 `inventoryCode`，格式：

```text
RM:{materialGrade}-{width}x{length}x{thickness}-{YYYYMMDD}-{id}
```

例如：

```text
RM:Q235-1200x800x2.5-20260605-10
```

需要按编码打开详情时，Qt 调用：

```text
GET /api/v1/inventory-items/by-code?inventoryCode=RM:Q235-1200x800x2.5-20260605-10
```

返回 `InventoryItem`。不要用 `materialId` 做库存定位，`materialId` 只表示材质主数据，
不能唯一定位库存项。

### XLSX 批量导入

```text
POST /api/v1/inventory-items/import-xlsx?dryRun=true
Content-Type: multipart/form-data
```

表单字段：

```text
file = inventory.xlsx
```

建议 Qt 流程：

1. 用户选择 XLSX。
2. 先调用 `dryRun=true` 预览。
3. 展示 `created` / `updated` / `errors`。
4. 用户确认后调用 `dryRun=false` 真正写入。

单次最多 200 行有效数据，超过返回：

```json
{
  "code": 400,
  "message": "inventory_xlsx_limit_exceeded",
  "data": null,
  "errorCode": "inventory_xlsx_limit_exceeded"
}
```

导入兼容以下列名：

```text
板材名称
图纸路径
宽
长
材质
厚度
数量
使用数量
```

说明：

- `板材名称` 和 `图纸路径` 可以存在，但后端导入时会忽略，不参与匹配、不入库、不校验。
- 后端只读取 `宽`、`长`、`材质`、`厚度`、`数量`、`使用数量`。
- 批量导入按 `宽 + 长 + 材质 + 厚度` 匹配库存规格。
- 匹配成功时，后端按 `使用数量` 扣减数据库现有 `quantity`，并写入本次 `remark`。
- 匹配失败时，后端新建库存规格，生成 `inventoryCode`，库存数按 `数量 - 使用数量` 计算。
- `使用数量` 为空或 0 时不扣库存，但仍写入本次计算备注。
- `使用数量` 大于库存数或导入数量时，库存数置 0，备注写明差额，交给人工判断。
- `材质 + 厚度` 不存在时，后端会自动创建材质主数据。
- 模板中没有的库存管理字段，例如 `inventoryType`、`source`、`location`、`status`、`reusable`，由 Qt 在导入后人工编辑补充。

成功响应 `data`：

```json
{
  "dryRun": true,
  "totalRows": 2,
  "validRows": 2,
  "created": 2,
  "updated": 0,
  "skipped": 0,
  "errors": [],
  "previewRows": [
    {
      "rowNumber": 2,
      "action": "create",
      "inventoryCode": null,
      "materialGrade": "Q235",
      "inventoryType": "leftover",
      "width": 1200,
      "length": 800,
      "thickness": 2.5,
      "quantity": 10,
      "usedQuantity": 3,
      "remark": "未匹配到库存，已新建。库存数 10 - 使用数量 3 = 7。",
      "source": "",
      "location": "",
      "status": "available",
      "reusable": true
    }
  ]
}
```

### XLSX 批量导出

```text
POST /api/v1/inventory-items/export-xlsx
```

请求：

```json
{
  "inventoryCodes": [
    "RM:Q235-1200x800x2.5-20260605-10"
  ]
}
```

成功时返回 XLSX 文件，保持 `Template.xlsx` 的 7 列顺序。单次最多导出 200 条
`inventoryCode`；Qt 应在前端选择时同步限制，并仍以服务端错误为准。

注意：

- 导出列固定为 `板材名称, 图纸路径, 宽, 长, 材质, 厚度, 数量`。
- `板材名称` 由后端填充为 `inventoryCode`。
- `图纸路径` 由后端导出为空字符串。
- 当前不导出二维码列；二维码打印功能待后续重新规划。

## 状态字典

`inventoryType`：

- `whole_sheet`：整板。
- `leftover`：余料。

`status`：

- `available`：可用。
- `reserved`：已占用。
- `consumed`：已消耗。
- `scrapped`：已报废。
- `voided`：已作废。

Qt 内部逻辑使用英文 key；中文只用于显示。

## 与备料功能的关系

后端已经预留备料项到库存项的关系：

```text
cutting_preparation_items.source_inventory_item_id -> material_inventory_items.id
```

这意味着后续“备料单选择某块余料”可以沿用当前库存项，不需要 Qt 端另建本地库存。

首版板材物料库存页面不需要直接实现备料单，但不要把库存数据做成本地文件真相源。
