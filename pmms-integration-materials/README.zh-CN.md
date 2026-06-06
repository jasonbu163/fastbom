# PMMS 板材物料库存接入材料包

本目录给 FastBOM / Qt 前端接入 AIIS-PMMS 后端使用。当前目标不是重写
FastBOM 的本地 BOM / SolidWorks / DXF 主链路，而是在现有 PySide6 桌面外壳中
新增最小的远程账号管理和板材物料库存管理工作流。

命名约定：

- Qt 页面显示建议使用“板材物料库存管理”，不要再写死“余料管理”。
- 后端 `materials` 表示材质 / 材料主数据，`material_inventory_items` 表示库存项。
- 当前库存类型已有 `whole_sheet`（整板 / 整料）和 `leftover`（余料），都属于当前板材物料库存范围。
- 当前 XLSX 导入 / 导出模板和前端功能围绕板材类物料；管材、型材等物料形态需要后续单独规划。

## 当前前端阶段

FastBOM 的 `PLAN.zh-CN.md` 已经把远程 API 接入放在第三阶段：

- 新增 `services/remote_api.py` 作为 HTTP client 边界。
- 新增 `gui/pages/remote_form_page.py` 或更具体的业务页面。
- 读取后端 `openapi.json` 后再实现请求和响应解析。
- 使用设置页中的后端 API URL 和超时。
- 普通登录走后端认证 API。
- 不在页面里硬编码 URL、token、payload 拼接或响应字段转换。

## 本次 PMMS 最小目标

先实现“账号管理 + 板材物料库存管理”的最小功能：

1. 登录 PMMS 后端。
2. root/admin 按权限管理用户。
3. 用户修改自己的密码。
4. 查看材质主数据。
5. 新增材质主数据。
6. 查看板材物料库存列表，支持整板 / 余料筛选。
7. 新增库存项。
8. 编辑库存项。
9. 作废库存项。
10. 批量导入板材物料库存 XLSX。
11. 按选中的 `inventoryCode` 批量导出同模板 XLSX。
12. 通过库存编码 `inventoryCode` 定位库存项。

不在 Qt 端先做：

- 生产报告 PDF 识别。
- 自动生成余料。
- 日结 / 月结锁定。
- 复杂库存流水。
- 长期 mock API。

## 文件说明

- `backend-api-contract.zh-CN.md`：后端 API、认证、响应信封、状态值和错误处理。
- `user-management-api.zh-CN.md`：root/admin 用户 CRUD、密码修改和 root 重置脚本契约。
- `residual-material-page-spec.zh-CN.md`：Qt 页面、表格、表单、交互和验收说明。
- `sample-payloads.json`：前端联调时可直接参考的请求 / 响应样例。
- `handoff-checklist.zh-CN.md`：实现前、中、后的检查清单。

## 后端基线

PMMS 后端地址由 Qt 设置页中的 `FASTBOM_API_BASE_URL` / 用户设置提供，例如：

```text
http://127.0.0.1:8000
```

业务接口前缀当前为：

```text
/api/v1
```

后端当前验证基线：

```bash
cd /Users/jason/Desktop/DreamCode/AIIS-PMMS/backend
uv run pytest
```

最近一次检查结果以本目录交付时实际后端验证输出为准。
