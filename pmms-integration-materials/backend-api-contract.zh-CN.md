# PMMS 后端 API 契约

本文只记录 Qt 余料管理首版需要消费的后端契约。以后如果后端
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

## 材质主数据

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
- 余料新增前必须有对应 `materialId`。
- Qt 可以先做“选择已有材质”，再补“快速新增材质”按钮。

## 库存 / 余料

### 列表

```text
GET /api/v1/inventory-items
```

支持查询参数：

```text
materialId
inventoryType
status
reusable
minWidth
minLength
materialGrade
thickness
```

余料列表常用查询：

```text
GET /api/v1/inventory-items?inventoryType=leftover&status=available
```

成功响应 `data[]`：

```json
{
  "id": 10,
  "materialId": 1,
  "materialGrade": "Q235",
  "inventoryType": "leftover",
  "width": 1200,
  "length": 800,
  "thickness": 2.5,
  "quantity": 1,
  "source": "manual-entry",
  "location": "A-01",
  "status": "available",
  "reusable": true
}
```

### 新增库存项

```text
POST /api/v1/inventory-items
```

请求：

```json
{
  "materialId": 1,
  "inventoryType": "leftover",
  "width": 1200,
  "length": 800,
  "thickness": 2.5,
  "quantity": 1,
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

首版余料页面不需要直接实现备料单，但不要把库存数据做成本地文件真相源。
