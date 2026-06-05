# PMMS 用户管理 API 契约

本文给 Qt 前端实现用户管理功能使用。首版建议做成“账号管理”页面或设置页中的
账号管理区域。

## 权限模型

root 身份：

```text
当前登录用户名 == 后端 BOOTSTRAP_ROOT_USERNAME
```

角色：

```text
root > admin > operator / viewer
```

说明：

- `operator` 是已有接口材料中的普通操作员角色，权限按普通账户处理。
- `viewer` 是默认普通账户角色。
- FastBOM 本机设置里的兜底 `admin` 不是后端 root。
- Qt 端业务判断使用英文 role/status key，中文只用于显示。

## 权限矩阵

| 当前用户 | 可管理对象 | 创建 | 查看 | 修改资料/角色/状态 | 删除 | 重置密码 |
| --- | --- | --- | --- | --- | --- | --- |
| root | admin / operator / viewer | 可以 | 可以 | 可以 | 可以 | 可以，无需旧密码 |
| root | 自己 | 不适用 | 可以 | 只建议改显示名 | 不可以 | 必须提供旧密码 |
| admin | operator / viewer | 可以 | 可以 | 可以 | 可以 | 可以，无需旧密码 |
| admin | root / admin | 不可以 | 不可以 | 不可以 | 不可以 | 不可以 |
| operator / viewer | 自己 | 不可以 | 可通过 `/auth/me` 查看 | 不建议开放 | 不可以 | 必须提供旧密码 |

删除接口实际执行软删除：

```text
status = disabled
```

不要在 Qt 里把删除理解成数据库物理删除。

## 用户对象

```json
{
  "username": "viewer01",
  "displayName": "Viewer 01",
  "role": "viewer",
  "status": "active"
}
```

当前允许的 `role`：

- `admin`
- `operator`
- `viewer`

当前允许的 `status`：

- `active`
- `disabled`

## 列表

```text
GET /api/v1/users
Authorization: Bearer <accessToken>
```

规则：

- root 返回所有用户。
- admin 只返回普通账户：`operator` / `viewer`。
- 普通账户调用返回 403。

## 查看单个用户

```text
GET /api/v1/users/{username}
Authorization: Bearer <accessToken>
```

规则：

- root 可查看所有用户。
- admin 只能查看普通账户。
- 用户可以查看自己；普通自我信息通常优先使用 `/api/v1/auth/me`。

## 创建用户

```text
POST /api/v1/users
Authorization: Bearer <accessToken>
```

请求：

```json
{
  "username": "viewer01",
  "password": "password-from-user-input",
  "displayName": "Viewer 01",
  "role": "viewer",
  "status": "active"
}
```

规则：

- root 可创建 `admin` / `operator` / `viewer`。
- admin 只能创建 `operator` / `viewer`。
- 普通账户不能创建用户。
- 响应不返回密码，也不返回密码 hash。

## 修改用户资料 / 角色 / 状态

```text
PATCH /api/v1/users/{username}
Authorization: Bearer <accessToken>
```

请求可以只传变更字段：

```json
{
  "displayName": "Viewer Updated",
  "role": "viewer",
  "status": "active"
}
```

规则：

- root 可修改非 root 用户。
- root 自己不允许通过该接口修改自己的 `role` / `status`。
- admin 只能修改普通账户。
- admin 不能把普通账户提升为 `admin`。

## 修改 / 重置密码

```text
PATCH /api/v1/users/{username}/password
Authorization: Bearer <accessToken>
```

自己改密码必须提供旧密码：

```json
{
  "oldPassword": "old-password-from-user-input",
  "newPassword": "new-password-from-user-input"
}
```

上级重置下级密码不需要旧密码：

```json
{
  "newPassword": "new-password-from-user-input"
}
```

规则：

- root 改自己的密码：必须提供 `oldPassword`。
- root 重置 admin / operator / viewer：无需旧密码。
- admin 重置 operator / viewer：无需旧密码。
- operator / viewer 改自己的密码：必须提供 `oldPassword`。

## 删除用户

```text
DELETE /api/v1/users/{username}
Authorization: Bearer <accessToken>
```

规则：

- root 不能删除自己。
- root 可删除非 root 用户。
- admin 只能删除普通账户。
- 删除返回的用户对象中 `status == "disabled"`。

## 错误处理

未登录：

```text
HTTP 401
```

越权：

```json
{
  "code": 403,
  "message": "user_permission_denied",
  "data": null,
  "errorCode": "user_permission_denied"
}
```

不能删除自己：

```json
{
  "code": 403,
  "message": "cannot_delete_self",
  "data": null,
  "errorCode": "cannot_delete_self"
}
```

自己改密码未提供旧密码：

```json
{
  "code": 400,
  "message": "old_password_required",
  "data": null,
  "errorCode": "old_password_required"
}
```

旧密码错误：

```json
{
  "code": 400,
  "message": "invalid_old_password",
  "data": null,
  "errorCode": "invalid_old_password"
}
```

用户名重复：

```json
{
  "code": 400,
  "message": "user_already_exists",
  "data": null,
  "errorCode": "user_already_exists"
}
```

## root 密码保底脚本

如果 root 忘记密码，在 PMMS 后端项目中运行：

```bash
cd /Users/jason/Desktop/DreamCode/AIIS-PMMS/backend
uv run python scripts/reset_root_password.py
```

脚本行为：

- 读取 `.env` 中的 `BOOTSTRAP_ROOT_USERNAME` 和 `BOOTSTRAP_ROOT_PASSWORD`。
- 如果 root 存在，重置 root 密码 hash 为 `.env` 初始密码。
- 如果 root 缺失，创建 root。
- 强制 root 为 `role=admin`、`status=active`。
- 不打印明文密码。

成功输出示例：

```text
root_password_reset action=updated username=root role=admin status=active
```

## Qt 页面建议

推荐功能：

- 当前登录用户显示。
- root/admin 可见的账号列表。
- 新增用户。
- 编辑用户显示名、角色、状态。
- 重置下级用户密码。
- 修改自己密码。
- 删除用户时提示“将禁用账号，不会删除历史记录”。

安全要求：

- 密码输入框使用密码模式。
- 创建 / 修改密码成功后清空密码输入框。
- 请求日志和 UI 摘要不展示密码。
- 非 root / admin 登录时隐藏账号管理页面，只保留“修改自己密码”入口。
