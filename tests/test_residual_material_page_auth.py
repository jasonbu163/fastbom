import os
import unittest
from datetime import datetime
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, QThread, QTimer, Qt
from PySide6.QtWidgets import QApplication

from auth.session import AuthSession
from config import AppSettings
from gui.pages.residual_material_page import ApiCallWorker, MaterialSpecDialog, ResidualMaterialPage
from services import RemoteApiResponseError


class ResidualMaterialPageAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_page_has_no_own_login_button(self):
        page = ResidualMaterialPage(
            settings=AppSettings(),
            auth_session=AuthSession.fallback_admin("admin"),
        )

        self.assertFalse(hasattr(page, "login_btn"))
        self.assertFalse(hasattr(page, "edit_item_btn"))
        self.assertFalse(hasattr(page, "void_item_btn"))

    def test_fallback_admin_disables_remote_actions(self):
        page = ResidualMaterialPage(
            settings=AppSettings(),
            auth_session=AuthSession.fallback_admin("admin"),
        )

        self.assertFalse(page.refresh_btn.isEnabled())
        self.assertFalse(page.add_material_btn.isEnabled())
        self.assertFalse(page.material_specs_btn.isEnabled())
        self.assertFalse(page.stock_in_btn.isEnabled())
        self.assertFalse(page.consume_btn.isEnabled())
        self.assertIn("离线", page.login_state_label.text())

    def test_backend_user_enables_remote_actions_and_sets_client_session(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
            display_name="操作员",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        self.assertTrue(page.refresh_btn.isEnabled())
        self.assertTrue(page.add_material_btn.isEnabled())
        self.assertTrue(page.stock_in_btn.isEnabled())
        self.assertTrue(page.consume_btn.isEnabled())
        self.assertEqual(page.stock_in_btn.text(), "入库")
        self.assertEqual(page.consume_btn.text(), "扣减 / 领用")
        self.assertEqual(page.material_specs_btn.text(), "物料规格")
        self.assertEqual(page.client.session.access_token, "access-token")
        self.assertIn("操作员", page.user_label.text())

    def test_material_spec_dialog_loads_paginated_materials(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        calls = []

        def run_api(status, call, on_success):
            calls.append(status)
            on_success(
                {
                    "items": [
                        {
                            "id": 1,
                            "materialGrade": "Q235",
                            "thickness": 2.5,
                            "specDescription": "冷轧板",
                            "defaultUnit": "张",
                            "enabled": True,
                        }
                    ],
                    "meta": {"page": 1, "pageSize": 20, "total": 1},
                }
            )

        page._run_api = run_api

        dialog = MaterialSpecDialog(page)

        self.assertIn("正在刷新物料规格...", calls)
        self.assertEqual(dialog.table.rowCount(), 1)
        self.assertEqual(dialog.table.item(0, 0).text(), "Q235")
        self.assertEqual(dialog.table.item(0, 4).text(), "启用")
        self.assertEqual(dialog.total_label.text(), "共 1 条")
        dialog.table.selectRow(0)
        self.assertEqual(dialog._selected_material()["id"], 1)

    def test_material_spec_dialog_query_uses_filters(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page._run_api = lambda _status, _call, on_success: on_success(
            {"items": [], "meta": {"page": 1, "pageSize": 20, "total": 0}}
        )
        dialog = MaterialSpecDialog(page)
        dialog.grade_filter.setText("Q")
        dialog.thickness_filter.setValue(2.5)
        dialog.enabled_filter.setCurrentIndex(dialog.enabled_filter.findData(True))

        query = dialog._query()

        self.assertEqual(query["materialGrade"], "Q")
        self.assertEqual(query["thickness"], 2.5)
        self.assertTrue(query["enabled"])

    def test_material_edit_payload_only_includes_changed_fields(self):
        material = {
            "id": 1,
            "materialGrade": "Q235",
            "thickness": 2.5,
            "specDescription": "冷轧板",
            "defaultUnit": "张",
            "enabled": True,
        }

        payload = MaterialSpecDialog._material_payload(
            material,
            "Q235",
            2.5,
            "冷轧板-更新",
            "张",
            True,
        )

        self.assertEqual(payload, {"specDescription": "冷轧板-更新"})

    def test_material_in_use_error_is_operator_readable(self):
        worker = ApiCallWorker(
            1,
            lambda: (_ for _ in ()).throw(
                RemoteApiResponseError("material_in_use", error_code="material_in_use")
            ),
        )
        messages = []
        worker.failed.connect(messages.append)

        worker.run()

        self.assertIn("该规格已用于库存", messages[0])
        self.assertIn("material_in_use", messages[0])

    def test_inventory_page_response_updates_table_and_pagination(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_page_loaded(
            {
                "items": [
                    {
                        "id": 10,
                        "inventoryCode": "RM:CODE",
                        "materialId": 1,
                        "materialGrade": "Q235",
                        "inventoryType": "whole_sheet",
                        "width": 1200,
                        "length": 800,
                        "thickness": 2.5,
                        "quantity": 1,
                        "remark": "manual review",
                        "source": "manual-entry",
                        "location": "A-01",
                        "status": "available",
                        "reusable": True,
                        "createdAt": "2026-06-06T10:00:00",
                        "updatedAt": "2026-06-06T10:30:00",
                    }
                ],
                "meta": {"page": 2, "pageSize": 20, "total": 45},
            }
        )

        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.horizontalHeaderItem(0).text(), "")
        self.assertEqual(page.table.columnWidth(0), 58)
        self.assertEqual(page.table.item(0, 0).text(), "")
        self.assertEqual(page.table.horizontalHeaderItem(1).text(), "ID")
        self.assertEqual(page.table.item(0, 1).text(), "10")
        self.assertEqual(page.table.item(0, 2).text(), "RM:CODE")
        self.assertEqual(page.table.item(0, 3).text(), "整板")
        self.assertEqual(page.table.item(0, 9).text(), "manual review")
        self.assertEqual(page.table.item(0, 12).text(), "可用")
        self.assertIsInstance(page.table.item(0, 0).data(256), int)
        page.table.selectRow(0)
        self.assertEqual(page._selected_item()["id"], 10)
        self.assertEqual(page._selected_items(), [])
        page.table.item(0, 0).setCheckState(Qt.CheckState.Checked)
        self.assertEqual(page._selected_items()[0]["inventoryCode"], "RM:CODE")
        self.assertEqual(page.total_label.text(), "共 45 条")
        self.assertEqual(page.page_label.text(), "第 2 / 3 页")

    def test_select_all_header_toggles_current_page_export_selection(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_page_loaded(
            {
                "items": [
                    {"id": 1, "inventoryCode": "RM:1", "inventoryType": "leftover"},
                    {"id": 2, "inventoryCode": "RM:2", "inventoryType": "leftover"},
                    {"id": 3, "inventoryCode": "RM:3", "inventoryType": "leftover"},
                ],
                "meta": {"page": 1, "pageSize": 20, "total": 3},
            }
        )

        self.assertEqual(page.select_all_checkbox.checkState(), Qt.CheckState.Unchecked)

        page.select_all_checkbox.setCheckState(Qt.CheckState.Checked)

        self.assertEqual([item["inventoryCode"] for item in page._selected_items()], ["RM:1", "RM:2", "RM:3"])
        for row in range(page.table.rowCount()):
            self.assertEqual(page.table.item(row, 0).checkState(), Qt.CheckState.Checked)

        page.table.item(1, 0).setCheckState(Qt.CheckState.Unchecked)

        self.assertEqual(page.select_all_checkbox.checkState(), Qt.CheckState.PartiallyChecked)
        self.assertEqual([item["inventoryCode"] for item in page._selected_items()], ["RM:1", "RM:3"])

        page.select_all_checkbox.setCheckState(Qt.CheckState.Unchecked)

        self.assertEqual(page._selected_items(), [])
        for row in range(page.table.rowCount()):
            self.assertEqual(page.table.item(row, 0).checkState(), Qt.CheckState.Unchecked)

    def test_api_success_callback_runs_on_gui_thread(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        loop = QEventLoop()
        seen = {}

        def on_success(_result):
            seen["on_gui_thread"] = QThread.currentThread() == self.app.thread()
            loop.quit()

        page._run_api("测试线程...", lambda: {"ok": True}, on_success)
        QTimer.singleShot(3000, loop.quit)
        loop.exec()
        page.shutdown()

        self.assertTrue(seen["on_gui_thread"])

    def test_located_inventory_code_replaces_table_with_single_item(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_code_located(
            {
                "id": 11,
                "inventoryCode": "RM:LOCATED",
                "materialId": 1,
                "materialGrade": "Q235",
                "inventoryType": "leftover",
                "width": 100,
                "length": 200,
                "thickness": 2.0,
                "quantity": 1,
                "remark": "",
                "source": "",
                "location": "",
                "status": "available",
                "reusable": True,
            }
        )

        self.assertEqual(page.inventory_code_filter.text(), "RM:LOCATED")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 2).text(), "RM:LOCATED")
        self.assertEqual(page.total_label.text(), "共 1 条")

    def test_empty_inventory_page_shows_empty_state(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_page_loaded({"items": [], "meta": {"page": 1, "pageSize": 20, "total": 0}})

        self.assertEqual(page.table.rowCount(), 0)
        self.assertFalse(page.empty_label.isHidden())
        self.assertIn("没有符合条件的库存项", page.empty_label.text())
        self.assertEqual(page.total_label.text(), "共 0 条")

    def test_apply_filter_button_is_persistent_and_refreshes_inventory(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page.current_page = 3
        page.refresh_inventory = Mock()

        page.apply_filters_btn.click()

        self.assertEqual(page.current_page, 1)
        page.refresh_inventory.assert_called_once_with()

    def test_reset_filters_restores_default_query_and_refreshes(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page.inventory_code_filter.setText("RM")
        page.material_grade_filter.setText("Q")
        page.thickness_filter.setValue(2.5)
        page.inventory_type_filter.setCurrentIndex(page.inventory_type_filter.findData("leftover"))
        page.status_filter.setCurrentIndex(page.status_filter.findData("voided"))
        page.reusable_filter.setCurrentIndex(page.reusable_filter.findData(False))
        page.min_width_filter.setValue(100)
        page.min_length_filter.setValue(200)
        page.current_page = 3
        page.refresh_inventory = Mock()

        page.reset_filters_btn.click()

        query = page._inventory_query()
        self.assertEqual(page.current_page, 1)
        self.assertEqual(query["inventoryCode"], "")
        self.assertEqual(query["materialGrade"], "")
        self.assertEqual(query["thickness"], None)
        self.assertEqual(query["inventoryType"], "")
        self.assertEqual(query["status"], "")
        self.assertEqual(query["reusable"], None)
        self.assertEqual(query["minWidth"], None)
        self.assertEqual(query["minLength"], None)
        page.refresh_inventory.assert_called_once_with()

    def test_inventory_date_columns_display_and_sort(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_page_loaded(
            {
                "items": [
                    {
                        "id": 20,
                        "inventoryCode": "RM:LATE",
                        "inventoryType": "leftover",
                        "createdAt": "2026-06-06T10:30:00Z",
                        "updatedAt": "2026-06-06T11:30:00Z",
                    },
                    {
                        "id": 10,
                        "inventoryCode": "RM:EARLY",
                        "inventoryType": "leftover",
                        "createdAt": "2026-06-05T08:00:00Z",
                        "updatedAt": "2026-06-05T09:00:00Z",
                    },
                ],
                "meta": {"page": 1, "pageSize": 20, "total": 2},
            }
        )

        self.assertEqual(page.table.horizontalHeaderItem(14).text(), "创建日期")
        self.assertEqual(page.table.horizontalHeaderItem(15).text(), "更新日期")
        self.assertEqual(page.table.item(0, 14).text(), "2026-06-06 10:30:00")

        page.table.sortItems(14)

        self.assertEqual(page.table.item(0, 2).text(), "RM:EARLY")

    def test_consumed_status_displays_as_exhausted(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)

        page._on_inventory_page_loaded(
            {
                "items": [
                    {
                        "id": 30,
                        "inventoryCode": "RM:DONE",
                        "inventoryType": "leftover",
                        "status": "consumed",
                    }
                ],
                "meta": {"page": 1, "pageSize": 20, "total": 1},
            }
        )

        self.assertEqual(page.table.item(0, 12).text(), "已耗尽")

    def test_stock_in_allows_consumed_item_but_consume_blocks_it(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page._show_inventory_delta_dialog = Mock()
        page._on_inventory_page_loaded(
            {
                "items": [
                    {
                        "id": 30,
                        "inventoryCode": "RM:DONE",
                        "inventoryType": "leftover",
                        "quantity": 0,
                        "status": "consumed",
                    }
                ],
                "meta": {"page": 1, "pageSize": 20, "total": 1},
            }
        )
        page.table.selectRow(0)

        page._stock_in_selected_item()

        page._show_inventory_delta_dialog.assert_called_once_with(page.inventory_items[0], "stock_in")

        page._show_inventory_delta_dialog.reset_mock()
        with patch("gui.pages.residual_material_page.QMessageBox.warning") as warning:
            page._consume_selected_item()

        warning.assert_called_once()
        page._show_inventory_delta_dialog.assert_not_called()

    def test_default_query_shows_all_inventory_statuses(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page.inventory_code_filter.setText("RM:CODE")

        query = page._inventory_query()

        self.assertEqual(query["inventoryType"], "")
        self.assertEqual(query["status"], "")
        self.assertEqual(query["inventoryCode"], "RM:CODE")
        self.assertEqual(page.inventory_code_filter.placeholderText(), "库存编码片段 / 扫码内容")
        self.assertEqual(page.material_grade_filter.placeholderText(), "材质 / 牌号模糊搜索")

    def test_inventory_type_filter_adds_query_value_when_selected(self):
        remote_session = AuthSession.backend_user(
            username="operator",
            access_token="access-token",
            refresh_token="refresh-token",
        )
        page = ResidualMaterialPage(settings=AppSettings(), auth_session=remote_session)
        page.inventory_type_filter.setCurrentIndex(page.inventory_type_filter.findData("leftover"))

        query = page._inventory_query()

        self.assertEqual(query["inventoryType"], "leftover")

    def test_default_export_filename_uses_configured_prefix_and_timestamp(self):
        settings = AppSettings(inventory=type(AppSettings().inventory)(export_filename_prefix="现场库存"))

        filename = ResidualMaterialPage._default_export_filename(settings, datetime(2026, 6, 16, 14, 30, 25))

        self.assertEqual(filename, "现场库存-20260616-143025.xlsx")

    def test_local_time_display_does_not_convert_timezone(self):
        self.assertEqual(
            ResidualMaterialPage._format_local_datetime("2026-06-06T10:00:00+08:00"),
            "2026-06-06 10:00:00",
        )
        self.assertEqual(
            ResidualMaterialPage._format_local_datetime("2026-06-06T10:00:00Z"),
            "2026-06-06 10:00:00",
        )


if __name__ == "__main__":
    unittest.main()
