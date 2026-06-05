# PMMS 接入交接清单

## 实现前

- [ ] 阅读 `PLAN.zh-CN.md` 第三阶段“远程 API 表单页”。
- [ ] 阅读 `AGENTS.zh-CN.md` 的远程 API 契约规则。
- [ ] 确认后端服务可访问，例如 `GET /health`。
- [ ] 确认 Qt 设置页可以保存后端 API URL 和请求超时。
- [ ] 确认不在 Git 跟踪文件中写真实账号、密码、token。
- [ ] 从后端读取一次 `/openapi.json`，对照本目录文档。

## 实现中

- [ ] 新增或复用 `services/remote_api.py`。
- [ ] service 负责 URL 拼接、认证头、响应信封解析和错误归一。
- [ ] UI 页面不直接拼 URL。
- [ ] UI 页面不直接持久化真实密码。
- [ ] 用户管理按 root / admin / 普通账户权限矩阵显示或禁用动作。
- [ ] 删除用户调用 `DELETE /users/{username}`，并按 `status=disabled` 处理。
- [ ] 修改自己密码必须要求旧密码；重置下级用户密码不要求旧密码。
- [ ] 远程请求不阻塞 UI 线程。
- [ ] 状态 key 使用英文，中文只作为显示。
- [ ] 新增余料时先使用后端 `materials` 的 `id`。
- [ ] 作废余料调用 `/inventory-items/{id}/void`，不要本地删除行冒充成功。

## 联调顺序

1. `GET /health`。
2. `POST /api/v1/auth/login`。
3. `GET /api/v1/auth/me`。
4. root 会话：`POST /api/v1/users` 创建 admin。
5. admin 会话：`POST /api/v1/users` 创建 viewer。
6. root/admin 会话：`GET /api/v1/users`。
7. root/admin 会话：`PATCH /api/v1/users/{username}`。
8. root/admin 会话：`PATCH /api/v1/users/{username}/password`。
9. root/admin 会话：`DELETE /api/v1/users/{username}`。
10. 用户本人会话：`PATCH /api/v1/users/{username}/password`，带 `oldPassword`。
11. `GET /api/v1/materials?enabled=true`。
12. `POST /api/v1/materials`。
13. `GET /api/v1/inventory-items?inventoryType=leftover&status=available`。
14. `POST /api/v1/inventory-items`。
15. `PATCH /api/v1/inventory-items/{id}`。
16. `POST /api/v1/inventory-items/{id}/void`。

## 后端验证

在 PMMS 后端项目中运行：

```bash
cd /Users/jason/Desktop/DreamCode/AIIS-PMMS/backend
uv run pytest
```

通过后再说后端契约验证完成。

## Qt 验证

在 FastBOM 项目中运行：

```bash
uv run python -m compileall main.py config core gui utils build.py
```

如果改了 UI：

```bash
uv run python main.py
```

macOS 或没有 SolidWorks 的机器不能声称完整本地转换链路已验证；只能说明语法、
页面启动或远程 API 联调情况。
