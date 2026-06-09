from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping, Optional

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from auth import AuthSession
from config import AppSettings
from services import (
    RemoteApiClient,
    RemoteApiError,
    RemoteApiResponseError,
)


STATUS_LABELS = {
    "available": "可用",
    "reserved": "已占用",
    "consumed": "已消耗",
    "scrapped": "已报废",
    "voided": "已作废",
}

INVENTORY_TYPE_LABELS = {
    "whole_sheet": "整板",
    "leftover": "余料",
}

REMOTE_ERROR_MESSAGES = {
    "material_in_use": "该规格已用于库存，不能修改材质 / 牌号或厚度。",
    "material_already_exists": "已存在相同材质 / 牌号和厚度的物料规格。",
    "material_not_found": "物料规格不存在或已被移除。",
}


class ApiCallWorker(QObject):
    finished = Signal(int, object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, request_id: int, call: Callable[[], Any]):
        super().__init__()
        self.request_id = request_id
        self.call = call

    def run(self) -> None:
        try:
            self.finished.emit(self.request_id, self.call())
        except RemoteApiResponseError as exc:
            message = REMOTE_ERROR_MESSAGES.get(exc.error_code, str(exc))
            suffix = f"（{exc.error_code}）" if exc.error_code else ""
            self.failed.emit(f"{message}{suffix}")
        except RemoteApiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"远程请求失败：{exc}")
        finally:
            self.done.emit()


class SortableTableWidgetItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(Qt.ItemDataRole.UserRole + 1)
        right = other.data(Qt.ItemDataRole.UserRole + 1)
        if left is not None and right is not None:
            return float(left) < float(right)
        return self.text() < other.text()


class MaterialSpecDialog(QDialog):
    def __init__(self, page: "ResidualMaterialPage"):
        super().__init__(page)
        self.page = page
        self.materials: list[Mapping[str, Any]] = []
        self.current_page = 1
        self.page_size = 20
        self.total_items = 0

        self.setWindowTitle("物料规格")
        self.resize(780, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        filter_row = QHBoxLayout()
        self.grade_filter = QLineEdit()
        self.grade_filter.setPlaceholderText("材质 / 牌号")
        self.thickness_filter = QDoubleSpinBox()
        self.thickness_filter.setRange(0.0, 1000.0)
        self.thickness_filter.setDecimals(2)
        self.thickness_filter.setSpecialValueText("不限")
        self.enabled_filter = QComboBox()
        self.enabled_filter.addItem("全部", None)
        self.enabled_filter.addItem("启用", True)
        self.enabled_filter.addItem("禁用", False)
        self.apply_btn = QPushButton("筛选")
        self.apply_btn.clicked.connect(self.apply_filters)
        filter_row.addWidget(QLabel("材质"))
        filter_row.addWidget(self.grade_filter, 1)
        filter_row.addWidget(QLabel("厚度"))
        filter_row.addWidget(self.thickness_filter)
        filter_row.addWidget(QLabel("状态"))
        filter_row.addWidget(self.enabled_filter)
        filter_row.addWidget(self.apply_btn)
        layout.addLayout(filter_row)

        action_row = QHBoxLayout()
        self.add_btn = QPushButton("新增")
        self.edit_btn = QPushButton("编辑")
        self.toggle_enabled_btn = QPushButton("启用 / 禁用")
        self.refresh_btn = QPushButton("刷新")
        self.add_btn.clicked.connect(lambda: self._show_material_form())
        self.edit_btn.clicked.connect(self._edit_selected_material)
        self.toggle_enabled_btn.clicked.connect(self._toggle_selected_material)
        self.refresh_btn.clicked.connect(self.refresh)
        action_row.addWidget(self.add_btn)
        action_row.addWidget(self.edit_btn)
        action_row.addWidget(self.toggle_enabled_btn)
        action_row.addStretch()
        action_row.addWidget(self.refresh_btn)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["材质 / 牌号", "厚度", "规格说明", "默认单位", "状态", "ID"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected_material)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 220)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 80)
        self.table.setColumnWidth(5, 70)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)

        pagination = QHBoxLayout()
        self.total_label = QLabel("共 0 条")
        self.page_label = QLabel("第 1 / 1 页")
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 200)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self.change_page_size)
        self.prev_page_btn = QPushButton("上一页")
        self.next_page_btn = QPushButton("下一页")
        self.prev_page_btn.clicked.connect(self.previous_page)
        self.next_page_btn.clicked.connect(self.next_page)
        pagination.addWidget(self.total_label)
        pagination.addStretch()
        pagination.addWidget(QLabel("每页"))
        pagination.addWidget(self.page_size_spin)
        pagination.addWidget(self.prev_page_btn)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next_page_btn)
        layout.addLayout(pagination)

        self.refresh()

    def apply_filters(self) -> None:
        self.current_page = 1
        self.refresh()

    def previous_page(self) -> None:
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self.refresh()

    def next_page(self) -> None:
        if self.current_page >= self._total_pages():
            return
        self.current_page += 1
        self.refresh()

    def change_page_size(self, page_size: int) -> None:
        self.page_size = page_size
        self.current_page = 1
        self.refresh()

    def refresh(self) -> None:
        self.page._run_api(
            "正在刷新物料规格...",
            lambda: self.page.client.page_materials(self._query(), self.current_page, self.page_size),
            self._on_material_page_loaded,
        )

    def _query(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled_filter.currentData(),
            "materialGrade": self.grade_filter.text().strip(),
            "thickness": self.thickness_filter.value() or None,
        }

    def _on_material_page_loaded(self, page_data: Mapping[str, Any]) -> None:
        meta = dict(page_data.get("meta") or {})
        self.current_page = int(meta.get("page") or self.current_page)
        self.page_size = int(meta.get("pageSize") or self.page_size)
        self.total_items = int(meta.get("total") or 0)
        if self.page_size_spin.value() != self.page_size:
            self.page_size_spin.blockSignals(True)
            self.page_size_spin.setValue(self.page_size)
            self.page_size_spin.blockSignals(False)
        self.materials = list(page_data.get("items") or [])
        self.table.setRowCount(len(self.materials))
        for row, material in enumerate(self.materials):
            values = [
                material.get("materialGrade"),
                material.get("thickness"),
                material.get("specDescription"),
                material.get("defaultUnit"),
                "启用" if material.get("enabled") else "禁用",
                material.get("id"),
            ]
            for col, value in enumerate(values):
                table_item = SortableTableWidgetItem("" if value is None else str(value))
                table_item.setData(Qt.ItemDataRole.UserRole, int(material["id"]))
                if col in (1, 5):
                    table_item.setData(Qt.ItemDataRole.UserRole + 1, float(value or 0))
                self.table.setItem(row, col, table_item)
        self._refresh_pagination_labels()

    def _edit_selected_material(self) -> None:
        material = self._selected_material()
        if material is None:
            QMessageBox.information(self, "物料规格", "请先选择一条物料规格。")
            return
        self._show_material_form(material)

    def _toggle_selected_material(self) -> None:
        material = self._selected_material()
        if material is None:
            QMessageBox.information(self, "物料规格", "请先选择一条物料规格。")
            return
        enabled = not bool(material.get("enabled"))
        action = "启用" if enabled else "禁用"
        material_id = int(material["id"])
        if QMessageBox.question(self, "物料规格", f"确认{action}物料规格 #{material_id}？") != QMessageBox.StandardButton.Yes:
            return
        self.page._run_api(
            f"正在{action}物料规格...",
            lambda: self.page.client.update_material(material_id, {"enabled": enabled}),
            self._after_material_changed,
        )

    def _show_material_form(self, material: Optional[Mapping[str, Any]] = None) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑物料规格" if material else "新增物料规格")
        form = QFormLayout(dialog)
        grade_edit = QLineEdit(str(material.get("materialGrade") or "") if material else "")
        thickness_spin = QDoubleSpinBox()
        thickness_spin.setRange(0.01, 1000.0)
        thickness_spin.setDecimals(2)
        thickness_spin.setValue(float((material or {}).get("thickness") or 0.01))
        spec_edit = QLineEdit(str((material or {}).get("specDescription") or ""))
        unit_edit = QLineEdit(str((material or {}).get("defaultUnit") or "张"))
        enabled_check = QCheckBox("启用")
        enabled_check.setChecked(bool((material or {"enabled": True}).get("enabled")))
        form.addRow("材质 / 牌号", grade_edit)
        form.addRow("厚度", thickness_spin)
        form.addRow("规格说明", spec_edit)
        form.addRow("默认单位", unit_edit)
        form.addRow("状态", enabled_check)
        if material:
            note = QLabel("已被库存引用的规格，后端会拒绝修改材质 / 厚度。")
            note.setWordWrap(True)
            form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not grade_edit.text().strip():
            QMessageBox.warning(self, "物料规格", "请输入材质 / 牌号。")
            return
        payload = self._material_payload(
            material,
            grade_edit.text().strip(),
            thickness_spin.value(),
            spec_edit.text().strip(),
            unit_edit.text().strip() or "张",
            enabled_check.isChecked(),
        )
        if material:
            if not payload:
                QMessageBox.information(self, "物料规格", "没有需要保存的变更。")
                return
            material_id = int(material["id"])
            self.page._run_api(
                "正在更新物料规格...",
                lambda: self.page.client.update_material(material_id, payload),
                self._after_material_changed,
            )
        else:
            self.page._run_api(
                "正在新增物料规格...",
                lambda: self.page.client.create_material(payload),
                self._after_material_changed,
            )

    @staticmethod
    def _material_payload(
        material: Optional[Mapping[str, Any]],
        material_grade: str,
        thickness: float,
        spec_description: str,
        default_unit: str,
        enabled: bool,
    ) -> dict[str, Any]:
        payload = {
            "materialGrade": material_grade,
            "thickness": thickness,
            "specDescription": spec_description,
            "defaultUnit": default_unit,
            "enabled": enabled,
        }
        if material is None:
            return payload

        changed: dict[str, Any] = {}
        if str(material.get("materialGrade") or "") != material_grade:
            changed["materialGrade"] = material_grade
        if abs(float(material.get("thickness") or 0) - thickness) > 0.000001:
            changed["thickness"] = thickness
        if str(material.get("specDescription") or "") != spec_description:
            changed["specDescription"] = spec_description
        if str(material.get("defaultUnit") or "") != default_unit:
            changed["defaultUnit"] = default_unit
        if bool(material.get("enabled")) != enabled:
            changed["enabled"] = enabled
        return changed

    def _after_material_changed(self, _material: Mapping[str, Any]) -> None:
        self.refresh()
        self.page.refresh_all()

    def _selected_material(self) -> Optional[Mapping[str, Any]]:
        row = self.table.currentRow()
        if row < 0:
            return None
        table_item = self.table.item(row, 0)
        if table_item is None:
            return None
        material_id = table_item.data(Qt.ItemDataRole.UserRole)
        for material in self.materials:
            if int(material.get("id", 0)) == int(material_id or 0):
                return material
        return None

    def _refresh_pagination_labels(self) -> None:
        total_pages = self._total_pages()
        self.total_label.setText(f"共 {self.total_items} 条")
        self.page_label.setText(f"第 {self.current_page} / {total_pages} 页")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def _total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return max(1, (self.total_items + self.page_size - 1) // self.page_size)


class ResidualMaterialPage(QWidget):
    def __init__(
        self,
        settings: AppSettings,
        auth_session: AuthSession,
        client: Optional[RemoteApiClient] = None,
    ):
        super().__init__()
        self.settings = settings
        self.auth_session = auth_session
        self.client = client or RemoteApiClient(settings.remote_api)
        self.client.set_session(auth_session.remote_api_session)
        self.current_user: Optional[Mapping[str, Any]] = None
        self.materials: list[Mapping[str, Any]] = []
        self.inventory_items: list[Mapping[str, Any]] = []
        self.pending_import_path = ""
        self.current_page = 1
        self.page_size = 20
        self.total_items = 0
        self._threads: list[QThread] = []
        self._workers: list[ApiCallWorker] = []
        self._worker_callbacks: dict[int, Callable[[Any], None]] = {}
        self._next_worker_id = 0
        self._closing = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(14)

        title = QLabel("板材物料库存管理")
        title.setObjectName("pageTitle")
        root_layout.addWidget(title)
        self._create_toolbar_group(root_layout)
        self._create_table_group(root_layout)
        self._refresh_connection_labels()

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.client.update_config(settings.remote_api)
        self._refresh_connection_labels()

    def shutdown(self) -> None:
        self._closing = True
        for thread in list(self._threads):
            thread.quit()
            if not thread.wait(max(1000, (self.settings.remote_api.timeout_seconds + 1) * 1000)):
                thread.wait()
        self._threads.clear()
        self._workers.clear()
        self._worker_callbacks.clear()

    def _create_toolbar_group(self, layout: QVBoxLayout) -> None:
        group_layout = QVBoxLayout()
        group_layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.api_url_label = QLabel()
        self.login_state_label = QLabel()
        self.user_label = QLabel()
        self.request_state_label = QLabel("尚未请求")
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_all)
        status_row.addWidget(QLabel("服务器"))
        status_row.addWidget(self.api_url_label, 1)
        status_row.addWidget(QLabel("会话"))
        status_row.addWidget(self.login_state_label)
        status_row.addWidget(QLabel("用户"))
        status_row.addWidget(self.user_label)
        status_row.addStretch()
        status_row.addWidget(self.refresh_btn)
        group_layout.addLayout(status_row)

        filter_grid = QGridLayout()
        filter_grid.setHorizontalSpacing(10)
        filter_grid.setVerticalSpacing(8)
        self.inventory_code_filter = QLineEdit()
        self.inventory_code_filter.setPlaceholderText("库存编码片段 / 扫码内容")
        self.inventory_code_filter.setMinimumWidth(170)
        self.material_grade_filter = QLineEdit()
        self.material_grade_filter.setPlaceholderText("材质 / 牌号模糊搜索")
        self.material_grade_filter.setMinimumWidth(120)
        self.thickness_filter = QDoubleSpinBox()
        self.thickness_filter.setRange(0.0, 1000.0)
        self.thickness_filter.setDecimals(2)
        self.thickness_filter.setSpecialValueText("不限")
        self.thickness_filter.setValue(0.0)
        self.thickness_filter.setMinimumWidth(92)
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", "")
        for key, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, key)
        self.status_filter.setCurrentIndex(max(0, self.status_filter.findData("available")))
        self._set_combo_min_width(self.status_filter, 112)
        self.inventory_type_filter = QComboBox()
        self.inventory_type_filter.addItem("全部", "")
        for key, label in INVENTORY_TYPE_LABELS.items():
            self.inventory_type_filter.addItem(label, key)
        self._set_combo_min_width(self.inventory_type_filter, 108)
        self.reusable_filter = QComboBox()
        self.reusable_filter.addItem("全部", None)
        self.reusable_filter.addItem("是", True)
        self.reusable_filter.addItem("否", False)
        self._set_combo_min_width(self.reusable_filter, 88)
        self.min_width_filter = QDoubleSpinBox()
        self.min_width_filter.setRange(0.0, 100000.0)
        self.min_width_filter.setSpecialValueText("不限")
        self.min_width_filter.setMinimumWidth(108)
        self.min_length_filter = QDoubleSpinBox()
        self.min_length_filter.setRange(0.0, 100000.0)
        self.min_length_filter.setSpecialValueText("不限")
        self.min_length_filter.setMinimumWidth(108)
        self.apply_filters_btn = QPushButton("应用筛选")
        self.apply_filters_btn.clicked.connect(self.apply_filters)
        self.reset_filters_btn = QPushButton("重置筛选")
        self.reset_filters_btn.clicked.connect(self.reset_filters)
        self.locate_code_btn = QPushButton("定位编码")
        self.locate_code_btn.clicked.connect(self.locate_inventory_code)
        filter_grid.addWidget(QLabel("编码"), 0, 0)
        filter_grid.addWidget(self.inventory_code_filter, 0, 1)
        filter_grid.addWidget(QLabel("类型"), 0, 2)
        filter_grid.addWidget(self.inventory_type_filter, 0, 3)
        filter_grid.addWidget(QLabel("状态"), 0, 4)
        filter_grid.addWidget(self.status_filter, 0, 5)
        filter_grid.addWidget(QLabel("材质"), 0, 6)
        filter_grid.addWidget(self.material_grade_filter, 0, 7)
        filter_grid.addWidget(QLabel("厚度"), 1, 0)
        filter_grid.addWidget(self.thickness_filter, 1, 1)
        filter_grid.addWidget(QLabel("复用"), 1, 2)
        filter_grid.addWidget(self.reusable_filter, 1, 3)
        filter_grid.addWidget(QLabel("最小宽"), 1, 4)
        filter_grid.addWidget(self.min_width_filter, 1, 5)
        filter_grid.addWidget(QLabel("最小长"), 1, 6)
        filter_grid.addWidget(self.min_length_filter, 1, 7)
        filter_grid.addWidget(self.locate_code_btn, 1, 8)
        filter_grid.addWidget(self.apply_filters_btn, 1, 9)
        filter_grid.addWidget(self.reset_filters_btn, 1, 10)
        filter_grid.setColumnStretch(1, 1)
        filter_grid.setColumnStretch(7, 1)
        group_layout.addLayout(filter_grid)

        request_row = QHBoxLayout()
        request_row.addWidget(QLabel("最近请求"))
        request_row.addWidget(self.request_state_label, 1)
        group_layout.addLayout(request_row)
        layout.addWidget(self._group("连接与筛选", group_layout))

    def _create_table_group(self, layout: QVBoxLayout) -> None:
        group_layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.import_xlsx_btn = QPushButton("导入 XLSX")
        self.import_xlsx_btn.clicked.connect(self.preview_inventory_xlsx)
        self.export_xlsx_btn = QPushButton("导出 XLSX")
        self.export_xlsx_btn.clicked.connect(self.export_selected_inventory_xlsx)
        self.material_specs_btn = QPushButton("物料规格")
        self.material_specs_btn.clicked.connect(self._show_material_specs_dialog)
        self.add_material_btn = self.material_specs_btn
        self.add_item_btn = QPushButton("新增库存项")
        self.add_item_btn.clicked.connect(lambda: self._show_inventory_dialog())
        actions.addWidget(self.material_specs_btn)
        actions.addWidget(self.import_xlsx_btn)
        actions.addWidget(self.export_xlsx_btn)
        actions.addStretch()
        actions.addWidget(self.add_item_btn)
        group_layout.addLayout(actions)

        self.table = QTableWidget(0, 16)
        self.table.setHorizontalHeaderLabels(
            [
                "",
                "ID",
                "库存编码",
                "类型",
                "材质",
                "厚度",
                "宽",
                "长",
                "数量",
                "备注",
                "来源",
                "库位",
                "状态",
                "可复用",
                "创建日期",
                "更新日期",
            ]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected_item)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self.table.setWordWrap(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSortIndicatorShown(False)
        header.setStretchLastSection(False)
        self._apply_table_column_widths()
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        group_layout.addWidget(self.table, 1)
        self.empty_label = QLabel("没有符合条件的库存项；可调整筛选或新增库存项。")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setVisible(False)
        group_layout.addWidget(self.empty_label)

        pagination = QHBoxLayout()
        self.total_label = QLabel("共 0 条")
        self.page_label = QLabel("第 1 / 1 页")
        self.prev_page_btn = QPushButton("上一页")
        self.prev_page_btn.clicked.connect(self.previous_page)
        self.next_page_btn = QPushButton("下一页")
        self.next_page_btn.clicked.connect(self.next_page)
        self.page_size_spin = QSpinBox()
        self.page_size_spin.setRange(1, 200)
        self.page_size_spin.setValue(self.page_size)
        self.page_size_spin.valueChanged.connect(self.change_page_size)
        pagination.addWidget(self.total_label)
        pagination.addStretch()
        pagination.addWidget(QLabel("每页"))
        pagination.addWidget(self.page_size_spin)
        pagination.addWidget(self.prev_page_btn)
        pagination.addWidget(self.page_label)
        pagination.addWidget(self.next_page_btn)
        group_layout.addLayout(pagination)

        table_group = self._group("板材物料库存", group_layout)
        table_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(table_group, 1)

    def refresh_all(self) -> None:
        query = self._inventory_query()
        self._run_api(
            "正在刷新材质和库存...",
            lambda: {
                "materials": self.client.list_materials(),
                "inventory_page": self.client.page_inventory_items(query, self.current_page, self.page_size),
            },
            self._on_refresh_all_loaded,
        )

    def refresh_inventory(self) -> None:
        query = self._inventory_query()
        self._run_api(
            "正在刷新库存...",
            lambda: self.client.page_inventory_items(query, self.current_page, self.page_size),
            self._on_inventory_page_loaded,
        )

    def apply_filters(self) -> None:
        self.current_page = 1
        self.refresh_inventory()

    def reset_filters(self) -> None:
        self.inventory_code_filter.clear()
        self.material_grade_filter.clear()
        self.thickness_filter.setValue(0.0)
        self.inventory_type_filter.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(max(0, self.status_filter.findData("available")))
        self.reusable_filter.setCurrentIndex(0)
        self.min_width_filter.setValue(0.0)
        self.min_length_filter.setValue(0.0)
        self.apply_filters()

    def previous_page(self) -> None:
        if self.current_page <= 1:
            return
        self.current_page -= 1
        self.refresh_inventory()

    def next_page(self) -> None:
        if self.current_page >= self._total_pages():
            return
        self.current_page += 1
        self.refresh_inventory()

    def change_page_size(self, page_size: int) -> None:
        self.page_size = page_size
        self.current_page = 1
        self.refresh_inventory()

    def locate_inventory_code(self) -> None:
        inventory_code = self.inventory_code_filter.text().strip()
        if not inventory_code:
            QMessageBox.information(self, "库存编码", "请输入或扫码库存编码。")
            return
        self._run_api(
            "正在定位库存编码...",
            lambda: self.client.get_inventory_item_by_code(inventory_code),
            self._on_inventory_code_located,
        )

    def preview_inventory_xlsx(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择库存 XLSX",
            "",
            "Excel 文件 (*.xlsx)",
        )
        if not file_path:
            return
        self.pending_import_path = file_path
        self._run_api(
            "正在预览导入...",
            lambda: self.client.preview_inventory_xlsx(file_path),
            self._on_import_preview_loaded,
        )

    def export_selected_inventory_xlsx(self) -> None:
        items = self._selected_items()
        if not items:
            QMessageBox.information(self, "导出 XLSX", "请先勾选需要导出的库存项。")
            return
        inventory_codes = [str(item.get("inventoryCode") or "") for item in items if item.get("inventoryCode")]
        if len(inventory_codes) != len(items):
            QMessageBox.warning(self, "导出 XLSX", "选中库存项存在缺失库存编码的记录，不能导出。")
            return
        if len(inventory_codes) > 200:
            QMessageBox.warning(self, "导出 XLSX", "单次最多导出 200 条库存项。")
            return
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存库存 XLSX",
            "inventory-items.xlsx",
            "Excel 文件 (*.xlsx)",
        )
        if not save_path:
            return
        if not save_path.lower().endswith(".xlsx"):
            save_path = f"{save_path}.xlsx"
        self._run_api(
            "正在导出 XLSX...",
            lambda: self.client.export_inventory_xlsx(inventory_codes),
            lambda content: self._on_export_xlsx_loaded(content, save_path),
        )

    def _show_material_specs_dialog(self) -> None:
        dialog = MaterialSpecDialog(self)
        dialog.exec()

    def _show_inventory_dialog(self, item: Optional[Mapping[str, Any]] = None) -> None:
        if not self.materials:
            QMessageBox.information(self, "库存项", "请先刷新材质列表。")
            self.refresh_all()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑库存项" if item else "新增库存项")
        form = QFormLayout(dialog)
        material_combo = QComboBox()
        for material in self.materials:
            material_id = int(material["id"])
            material_combo.addItem(
                f"{material.get('materialGrade')} / {material.get('thickness')}",
                material_id,
            )
        self._set_combo_min_width(material_combo, 220)
        inventory_type_combo = QComboBox()
        for key, label in INVENTORY_TYPE_LABELS.items():
            inventory_type_combo.addItem(label, key)
        inventory_type_combo.setCurrentIndex(max(0, inventory_type_combo.findData("leftover")))
        self._set_combo_min_width(inventory_type_combo, 120)
        width_spin = self._positive_double_spin()
        length_spin = self._positive_double_spin()
        thickness_spin = self._positive_double_spin()
        quantity_spin = QSpinBox()
        quantity_spin.setRange(1, 100000)
        remark_edit = QLineEdit()
        source_edit = QLineEdit("manual-entry")
        location_edit = QLineEdit()
        status_combo = QComboBox()
        for key, label in STATUS_LABELS.items():
            status_combo.addItem(label, key)
        self._set_combo_min_width(status_combo, 112)
        reusable_check = QCheckBox("可复用")
        reusable_check.setChecked(True)

        form.addRow("库存编码", QLabel(str(item.get("inventoryCode") or "") if item else "后端自动生成"))
        form.addRow("材质", material_combo)
        form.addRow("类型", inventory_type_combo)
        form.addRow("宽", width_spin)
        form.addRow("长", length_spin)
        form.addRow("厚度", thickness_spin)
        form.addRow("数量", quantity_spin)
        form.addRow("备注", remark_edit)
        form.addRow("来源", source_edit)
        form.addRow("库位", location_edit)
        form.addRow("状态", status_combo)
        form.addRow("可复用", reusable_check)

        if item:
            self._select_material(material_combo, int(item.get("materialId", 0)))
            inventory_type_combo.setCurrentIndex(max(0, inventory_type_combo.findData(item.get("inventoryType"))))
            width_spin.setValue(float(item.get("width") or 0))
            length_spin.setValue(float(item.get("length") or 0))
            thickness_spin.setValue(float(item.get("thickness") or 0))
            quantity_spin.setValue(int(item.get("quantity") or 1))
            remark_edit.setText(str(item.get("remark") or ""))
            source_edit.setText(str(item.get("source") or ""))
            location_edit.setText(str(item.get("location") or ""))
            status_combo.setCurrentIndex(max(0, status_combo.findData(item.get("status"))))
            reusable_check.setChecked(bool(item.get("reusable")))

        def fill_thickness() -> None:
            material = self._material_by_id(int(material_combo.currentData() or 0))
            if material and not item:
                thickness_spin.setValue(float(material.get("thickness") or 0))

        material_combo.currentIndexChanged.connect(fill_thickness)
        fill_thickness()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        material_id = int(material_combo.currentData() or 0)
        payload = {
            "materialId": material_id,
            "inventoryType": inventory_type_combo.currentData(),
            "width": width_spin.value(),
            "length": length_spin.value(),
            "thickness": thickness_spin.value(),
            "quantity": quantity_spin.value(),
            "remark": remark_edit.text().strip(),
            "source": source_edit.text().strip() or "manual-entry",
            "location": location_edit.text().strip(),
            "status": status_combo.currentData(),
            "reusable": reusable_check.isChecked(),
        }
        if item:
            item_id = int(item["id"])
            self._run_api(
                "正在更新库存项...",
                lambda: self.client.update_inventory_item(item_id, payload),
                self._after_inventory_changed,
            )
        else:
            self._run_api(
                "正在新增库存项...",
                lambda: self.client.create_inventory_item(payload),
                self._after_inventory_changed,
            )

    def _edit_selected_item(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "编辑库存项", "请先选择一条库存项。")
            return
        self._show_inventory_dialog(item)

    def _on_user_loaded(self, user: Mapping[str, Any]) -> None:
        self.current_user = user
        self.request_state_label.setText("已读取当前用户")
        self._refresh_connection_labels()

    def _on_materials_loaded(self, materials: list[Mapping[str, Any]]) -> None:
        self.materials = materials
        self.request_state_label.setText(f"已加载 {len(materials)} 条材质")

    def _on_refresh_all_loaded(self, result: Mapping[str, Any]) -> None:
        self.materials = list(result.get("materials") or [])
        self._on_inventory_page_loaded(dict(result.get("inventory_page") or {}))
        self.request_state_label.setText(f"已加载 {len(self.materials)} 条材质 / {len(self.inventory_items)} 条库存项")

    def _on_inventory_page_loaded(self, page_data: Mapping[str, Any]) -> None:
        meta = dict(page_data.get("meta") or {})
        self.current_page = int(meta.get("page") or self.current_page)
        self.page_size = int(meta.get("pageSize") or self.page_size)
        self.total_items = int(meta.get("total") or 0)
        if self.page_size_spin.value() != self.page_size:
            self.page_size_spin.blockSignals(True)
            self.page_size_spin.setValue(self.page_size)
            self.page_size_spin.blockSignals(False)
        self._on_inventory_loaded(list(page_data.get("items") or []))
        self._refresh_pagination_labels()

    def _on_inventory_code_located(self, item: Mapping[str, Any]) -> None:
        self.current_page = 1
        self.total_items = 1
        self.inventory_code_filter.setText(str(item.get("inventoryCode") or ""))
        self._on_inventory_loaded([item])
        self._refresh_pagination_labels()
        self.table.selectRow(0)
        self.request_state_label.setText("已定位库存编码")

    def _on_import_preview_loaded(self, result: Mapping[str, Any]) -> None:
        errors = list(result.get("errors") or [])
        preview_rows = list(result.get("previewRows") or [])
        summary = self._import_summary(result)
        if errors:
            error_text = "\n".join(
                f"第 {error.get('rowNumber')} 行：{error.get('message')}" for error in errors[:8]
            )
            QMessageBox.warning(self, "导入预览存在错误", f"{summary}\n\n{error_text}")
            self.request_state_label.setText("导入预览存在错误")
            return
        preview_text = "\n".join(
            f"第 {row.get('rowNumber')} 行 {row.get('action')}：{row.get('materialGrade')} "
            f"{row.get('width')}x{row.get('length')}x{row.get('thickness')}，"
            f"使用数量 {row.get('usedQuantity', 0)}，备注：{row.get('remark') or '无'}"
            for row in preview_rows[:8]
        )
        message = f"{summary}\n\n{preview_text}" if preview_text else summary
        if QMessageBox.question(self, "确认导入 XLSX", f"{message}\n\n确认写入库存？") != QMessageBox.StandardButton.Yes:
            self.request_state_label.setText("已取消导入")
            return
        file_path = self.pending_import_path
        self._run_api(
            "正在导入 XLSX...",
            lambda: self.client.import_inventory_xlsx(file_path),
            self._on_import_confirmed,
        )

    def _on_import_confirmed(self, result: Mapping[str, Any]) -> None:
        QMessageBox.information(self, "导入 XLSX", self._import_summary(result))
        self.request_state_label.setText("导入完成")
        self.current_page = 1
        self.refresh_all()

    def _on_export_xlsx_loaded(self, content: bytes, save_path: str) -> None:
        with open(save_path, "wb") as file:
            file.write(content)
        QMessageBox.information(self, "导出 XLSX", "库存文件已导出。")
        self.request_state_label.setText(f"已导出：{save_path}")

    def _on_inventory_loaded(self, items: list[Mapping[str, Any]]) -> None:
        self.inventory_items = items
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(items))
        if not items:
            self.empty_label.setVisible(True)
            self.request_state_label.setText("库存列表为空")
            self.table.setSortingEnabled(True)
            return
        self.empty_label.setVisible(False)
        for row, item in enumerate(items):
            created_at = self._date_value(item, ("createdAt", "created_at", "createTime", "create_time", "createdTime"))
            updated_at = self._date_value(item, ("updatedAt", "updated_at", "updateTime", "update_time", "updatedTime"))
            values = [
                item.get("id"),
                item.get("id"),
                item.get("inventoryCode"),
                INVENTORY_TYPE_LABELS.get(str(item.get("inventoryType")), item.get("inventoryType")),
                item.get("materialGrade"),
                item.get("thickness"),
                item.get("width"),
                item.get("length"),
                item.get("quantity"),
                item.get("remark"),
                item.get("source"),
                item.get("location"),
                STATUS_LABELS.get(str(item.get("status")), item.get("status")),
                "是" if item.get("reusable") else "否",
                self._format_local_datetime(created_at),
                self._format_local_datetime(updated_at),
            ]
            for col, value in enumerate(values):
                display_value = "" if col == 0 else "" if value is None else str(value)
                table_item = SortableTableWidgetItem(display_value)
                table_item.setData(Qt.ItemDataRole.UserRole, int(item["id"]))
                if col == 0:
                    table_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsUserCheckable
                    )
                    table_item.setCheckState(Qt.CheckState.Unchecked)
                    table_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                elif col in (1, 5, 6, 7, 8):
                    table_item.setData(Qt.ItemDataRole.UserRole + 1, float(value or 0))
                elif col == 14:
                    table_item.setData(Qt.ItemDataRole.UserRole + 1, self._date_sort_value(created_at))
                elif col == 15:
                    table_item.setData(Qt.ItemDataRole.UserRole + 1, self._date_sort_value(updated_at))
                self.table.setItem(row, col, table_item)
        self.table.setSortingEnabled(True)
        self.request_state_label.setText(f"已加载 {len(items)} 条库存项")

    def _after_create_material(self, _material: Mapping[str, Any]) -> None:
        self.request_state_label.setText("材质已新增")
        self.refresh_all()

    def _after_inventory_changed(self, _item: Mapping[str, Any]) -> None:
        self.request_state_label.setText("库存项已更新")
        self.refresh_inventory()

    def _refresh_pagination_labels(self) -> None:
        total_pages = self._total_pages()
        self.total_label.setText(f"共 {self.total_items} 条")
        self.page_label.setText(f"第 {self.current_page} / {total_pages} 页")
        self.prev_page_btn.setEnabled(self.current_page > 1)
        self.next_page_btn.setEnabled(self.current_page < total_pages)

    def _total_pages(self) -> int:
        if self.total_items <= 0:
            return 1
        return max(1, (self.total_items + self.page_size - 1) // self.page_size)

    def _run_api(self, status: str, call: Callable[[], Any], on_success: Callable[[Any], None]) -> None:
        if self._closing:
            return
        if not self.auth_session.can_use_remote_features:
            message = "当前为离线登录，无法使用远程板材物料库存管理功能。"
            self.request_state_label.setText(message)
            QMessageBox.information(self, "远程功能不可用", message)
            return
        self.request_state_label.setText(status)
        thread = QThread(self)
        self._next_worker_id += 1
        request_id = self._next_worker_id
        worker = ApiCallWorker(request_id, call)
        worker.moveToThread(thread)
        self._worker_callbacks[request_id] = on_success
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_api_success)
        worker.failed.connect(self._on_api_failed)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._cleanup_worker(thread, worker, request_id))
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        self._workers.append(worker)
        thread.start()

    @Slot(int, object)
    def _handle_api_success(self, request_id: int, result: Any) -> None:
        if self._closing:
            return
        on_success = self._worker_callbacks.get(request_id)
        if on_success is None:
            return
        on_success(result)

    def _cleanup_worker(self, thread: QThread, worker: ApiCallWorker, request_id: int) -> None:
        if thread in self._threads:
            self._threads.remove(thread)
        if worker in self._workers:
            self._workers.remove(worker)
        self._worker_callbacks.pop(request_id, None)

    def _on_api_failed(self, message: str) -> None:
        if self._closing:
            return
        self.request_state_label.setText(message)
        self._refresh_connection_labels()
        QMessageBox.warning(self, "远程请求失败", message)

    def _inventory_query(self) -> dict[str, Any]:
        query: dict[str, Any] = {
            "inventoryCode": self.inventory_code_filter.text().strip(),
            "inventoryType": self.inventory_type_filter.currentData(),
            "status": self.status_filter.currentData(),
            "reusable": self.reusable_filter.currentData(),
            "materialGrade": self.material_grade_filter.text().strip(),
            "thickness": self.thickness_filter.value() or None,
            "minWidth": self.min_width_filter.value() or None,
            "minLength": self.min_length_filter.value() or None,
        }
        return query

    def _selected_item(self) -> Optional[Mapping[str, Any]]:
        row = self.table.currentRow()
        if row < 0:
            return None
        table_item = self.table.item(row, 0)
        if table_item is None:
            return None
        item_id = table_item.data(Qt.ItemDataRole.UserRole)
        if item_id is None:
            return None
        return self._inventory_item_by_id(int(item_id))

    def _selected_items(self) -> list[Mapping[str, Any]]:
        items: list[Mapping[str, Any]] = []
        for row in range(self.table.rowCount()):
            table_item = self.table.item(row, 0)
            if table_item is None:
                continue
            if table_item.checkState() != Qt.CheckState.Checked:
                continue
            item_id = table_item.data(Qt.ItemDataRole.UserRole)
            if item_id is None:
                continue
            item = self._inventory_item_by_id(int(item_id))
            if item is not None:
                items.append(item)
        return items

    def _refresh_connection_labels(self) -> None:
        self.api_url_label.setText(self.settings.remote_api.base_url or "未配置")
        can_use_remote = self.auth_session.can_use_remote_features and self.client.session is not None
        if self.auth_session.can_use_remote_features and self.client.session is None:
            self.login_state_label.setText("登录失效")
        else:
            self.login_state_label.setText("服务器账号已登录" if can_use_remote else "离线登录，远程功能禁用")
        if self.current_user:
            display_name = self.current_user.get("displayName") or self.current_user.get("username")
            self.user_label.setText(str(display_name))
        else:
            self.user_label.setText(self.auth_session.display_name or self.auth_session.username)
        self.refresh_btn.setEnabled(can_use_remote)
        self.add_material_btn.setEnabled(can_use_remote)
        self.add_item_btn.setEnabled(can_use_remote)
        self.import_xlsx_btn.setEnabled(can_use_remote)
        self.export_xlsx_btn.setEnabled(can_use_remote)

    @staticmethod
    def _group(title: str, layout: QFormLayout | QVBoxLayout) -> QGroupBox:
        group = QGroupBox(title)
        group.setLayout(layout)
        return group

    @staticmethod
    def _positive_double_spin() -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0.01, 100000.0)
        spin.setDecimals(2)
        return spin

    @staticmethod
    def _set_combo_min_width(combo: QComboBox, width: int) -> None:
        combo.setMinimumWidth(width)
        combo.view().setMinimumWidth(width)

    def _apply_table_column_widths(self) -> None:
        widths = [58, 70, 190, 88, 110, 92, 100, 100, 82, 220, 150, 110, 100, 92, 160, 160]
        for column, width in enumerate(widths):
            self.table.setColumnWidth(column, width)

    @staticmethod
    def _date_value(item: Mapping[str, Any], keys: tuple[str, ...]) -> Any:
        for key in keys:
            value = item.get(key)
            if value:
                return value
        return None

    @staticmethod
    def _format_local_datetime(value: Any) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        text = text.replace("T", " ")
        if "." in text:
            text = text.split(".", 1)[0]
        if "+" in text:
            text = text.split("+", 1)[0]
        if text.endswith("Z"):
            text = text[:-1]
        return text[:19]

    @staticmethod
    def _date_sort_value(value: Any) -> float:
        parsed = ResidualMaterialPage._parse_datetime(value)
        if parsed is not None:
            return parsed.timestamp()
        return 0.0

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass
        for date_format in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, date_format)
            except ValueError:
                continue
        return None

    @staticmethod
    def _import_summary(result: Mapping[str, Any]) -> str:
        return (
            f"总行数 {result.get('totalRows', 0)}，有效 {result.get('validRows', 0)}，"
            f"新增 {result.get('created', 0)}，更新 {result.get('updated', 0)}，"
            f"跳过 {result.get('skipped', 0)}，错误 {len(result.get('errors') or [])}"
        )

    @staticmethod
    def _select_material(combo: QComboBox, material_id: int) -> None:
        for index in range(combo.count()):
            if int(combo.itemData(index) or 0) == material_id:
                combo.setCurrentIndex(index)
                return

    def _material_by_id(self, material_id: int) -> Optional[Mapping[str, Any]]:
        for material in self.materials:
            if int(material.get("id", 0)) == material_id:
                return material
        return None

    def _inventory_item_by_id(self, item_id: int) -> Optional[Mapping[str, Any]]:
        for item in self.inventory_items:
            if int(item.get("id", 0)) == item_id:
                return item
        return None
