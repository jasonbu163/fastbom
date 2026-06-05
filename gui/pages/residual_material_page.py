from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
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


class ApiCallWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)
    done = Signal()

    def __init__(self, call: Callable[[], Any]):
        super().__init__()
        self.call = call

    def run(self) -> None:
        try:
            self.finished.emit(self.call())
        except RemoteApiResponseError as exc:
            suffix = f"（{exc.error_code}）" if exc.error_code else ""
            self.failed.emit(f"{exc}{suffix}")
        except RemoteApiError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:
            self.failed.emit(f"远程请求失败：{exc}")
        finally:
            self.done.emit()


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
        self._threads: list[QThread] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(14)
        content_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("余料管理")
        title.setObjectName("pageTitle")
        content_layout.addWidget(title)
        self._create_connection_group(content_layout)
        self._create_filter_group(content_layout)
        self._create_table_group(content_layout)
        content_layout.addStretch()

        scroll.setWidget(content)
        root_layout.addWidget(scroll)
        self._refresh_connection_labels()

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.client.update_config(settings.remote_api)
        self._refresh_connection_labels()

    def _create_connection_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.api_url_label = QLabel()
        self.login_state_label = QLabel()
        self.user_label = QLabel()
        self.request_state_label = QLabel("尚未请求")
        form.addRow("后端 API", self.api_url_label)
        form.addRow("登录状态", self.login_state_label)
        form.addRow("当前用户", self.user_label)
        form.addRow("最近请求", self.request_state_label)

        actions = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新列表")
        self.refresh_btn.clicked.connect(self.refresh_all)
        actions.addStretch()
        actions.addWidget(self.refresh_btn)

        group_layout = QVBoxLayout()
        group_layout.addLayout(form)
        group_layout.addLayout(actions)
        layout.addWidget(self._group("连接状态", group_layout))

    def _create_filter_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        row1 = QHBoxLayout()
        self.material_grade_filter = QLineEdit()
        self.material_grade_filter.setPlaceholderText("例如 Q235")
        self.thickness_filter = QDoubleSpinBox()
        self.thickness_filter.setRange(0.0, 1000.0)
        self.thickness_filter.setDecimals(2)
        self.thickness_filter.setSpecialValueText("不限")
        self.thickness_filter.setValue(0.0)
        row1.addWidget(QLabel("材质"))
        row1.addWidget(self.material_grade_filter)
        row1.addWidget(QLabel("厚度"))
        row1.addWidget(self.thickness_filter)
        form.addRow(row1)

        row2 = QHBoxLayout()
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部", "")
        for key, label in STATUS_LABELS.items():
            self.status_filter.addItem(label, key)
        self.status_filter.setCurrentIndex(1)
        self.reusable_filter = QComboBox()
        self.reusable_filter.addItem("全部", None)
        self.reusable_filter.addItem("是", True)
        self.reusable_filter.addItem("否", False)
        row2.addWidget(QLabel("状态"))
        row2.addWidget(self.status_filter)
        row2.addWidget(QLabel("可复用"))
        row2.addWidget(self.reusable_filter)
        form.addRow(row2)

        row3 = QHBoxLayout()
        self.min_width_filter = QDoubleSpinBox()
        self.min_width_filter.setRange(0.0, 100000.0)
        self.min_width_filter.setSpecialValueText("不限")
        self.min_length_filter = QDoubleSpinBox()
        self.min_length_filter.setRange(0.0, 100000.0)
        self.min_length_filter.setSpecialValueText("不限")
        apply_btn = QPushButton("应用筛选")
        apply_btn.clicked.connect(self.refresh_inventory)
        row3.addWidget(QLabel("最小宽"))
        row3.addWidget(self.min_width_filter)
        row3.addWidget(QLabel("最小长"))
        row3.addWidget(self.min_length_filter)
        row3.addStretch()
        row3.addWidget(apply_btn)
        form.addRow(row3)
        layout.addWidget(self._group("筛选", form))

    def _create_table_group(self, layout: QVBoxLayout) -> None:
        group_layout = QVBoxLayout()
        actions = QHBoxLayout()
        self.add_material_btn = QPushButton("新增材质")
        self.add_material_btn.clicked.connect(self._show_material_dialog)
        self.add_item_btn = QPushButton("新增余料")
        self.add_item_btn.clicked.connect(lambda: self._show_inventory_dialog())
        self.edit_item_btn = QPushButton("编辑选中")
        self.edit_item_btn.clicked.connect(self._edit_selected_item)
        self.void_item_btn = QPushButton("作废选中")
        self.void_item_btn.clicked.connect(self._void_selected_item)
        actions.addStretch()
        actions.addWidget(self.add_material_btn)
        actions.addWidget(self.add_item_btn)
        actions.addWidget(self.edit_item_btn)
        actions.addWidget(self.void_item_btn)
        group_layout.addLayout(actions)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            ["ID", "材质", "厚度", "宽", "长", "数量", "来源", "库位", "状态", "可复用", "类型"]
        )
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._edit_selected_item)
        group_layout.addWidget(self.table)
        layout.addWidget(self._group("余料库存", group_layout))

    def refresh_all(self) -> None:
        self._run_api("正在刷新材质...", self.client.list_materials, self._on_materials_loaded)
        self.refresh_inventory()

    def refresh_inventory(self) -> None:
        self._run_api(
            "正在刷新余料...",
            lambda: self.client.list_inventory_items(self._inventory_query()),
            self._on_inventory_loaded,
        )

    def _show_material_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("新增材质")
        form = QFormLayout(dialog)
        grade_edit = QLineEdit()
        thickness_spin = QDoubleSpinBox()
        thickness_spin.setRange(0.01, 1000.0)
        thickness_spin.setDecimals(2)
        spec_edit = QLineEdit()
        unit_edit = QLineEdit("sheet")
        enabled_check = QCheckBox("启用")
        enabled_check.setChecked(True)
        form.addRow("材质牌号", grade_edit)
        form.addRow("厚度", thickness_spin)
        form.addRow("规格说明", spec_edit)
        form.addRow("默认单位", unit_edit)
        form.addRow("状态", enabled_check)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not grade_edit.text().strip():
            QMessageBox.warning(self, "新增材质", "请输入材质牌号。")
            return
        payload = {
            "materialGrade": grade_edit.text().strip(),
            "thickness": thickness_spin.value(),
            "specDescription": spec_edit.text().strip(),
            "defaultUnit": unit_edit.text().strip() or "sheet",
            "enabled": enabled_check.isChecked(),
        }
        self._run_api("正在新增材质...", lambda: self.client.create_material(payload), self._after_create_material)

    def _show_inventory_dialog(self, item: Optional[Mapping[str, Any]] = None) -> None:
        if not self.materials:
            QMessageBox.information(self, "余料", "请先刷新材质列表。")
            self.refresh_all()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("编辑余料" if item else "新增余料")
        form = QFormLayout(dialog)
        material_combo = QComboBox()
        for material in self.materials:
            material_combo.addItem(
                f"{material.get('materialGrade')} / {material.get('thickness')}",
                material,
            )
        width_spin = self._positive_double_spin()
        length_spin = self._positive_double_spin()
        thickness_spin = self._positive_double_spin()
        quantity_spin = QSpinBox()
        quantity_spin.setRange(1, 100000)
        source_edit = QLineEdit("manual-entry")
        location_edit = QLineEdit()
        status_combo = QComboBox()
        for key, label in STATUS_LABELS.items():
            status_combo.addItem(label, key)
        reusable_check = QCheckBox("可复用")
        reusable_check.setChecked(True)

        form.addRow("材质", material_combo)
        form.addRow("宽", width_spin)
        form.addRow("长", length_spin)
        form.addRow("厚度", thickness_spin)
        form.addRow("数量", quantity_spin)
        form.addRow("来源", source_edit)
        form.addRow("库位", location_edit)
        form.addRow("状态", status_combo)
        form.addRow("可复用", reusable_check)

        if item:
            self._select_material(material_combo, int(item.get("materialId", 0)))
            width_spin.setValue(float(item.get("width") or 0))
            length_spin.setValue(float(item.get("length") or 0))
            thickness_spin.setValue(float(item.get("thickness") or 0))
            quantity_spin.setValue(int(item.get("quantity") or 1))
            source_edit.setText(str(item.get("source") or ""))
            location_edit.setText(str(item.get("location") or ""))
            status_combo.setCurrentIndex(max(0, status_combo.findData(item.get("status"))))
            reusable_check.setChecked(bool(item.get("reusable")))

        def fill_thickness() -> None:
            material = material_combo.currentData()
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

        material = material_combo.currentData()
        payload = {
            "width": width_spin.value(),
            "length": length_spin.value(),
            "thickness": thickness_spin.value(),
            "quantity": quantity_spin.value(),
            "source": source_edit.text().strip() or "manual-entry",
            "location": location_edit.text().strip(),
            "status": status_combo.currentData(),
            "reusable": reusable_check.isChecked(),
        }
        if item:
            item_id = int(item["id"])
            self._run_api(
                "正在更新余料...",
                lambda: self.client.update_inventory_item(item_id, payload),
                self._after_inventory_changed,
            )
        else:
            payload.update({"materialId": int(material["id"]), "inventoryType": "leftover"})
            self._run_api(
                "正在新增余料...",
                lambda: self.client.create_inventory_item(payload),
                self._after_inventory_changed,
            )

    def _edit_selected_item(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "编辑余料", "请先选择一条余料。")
            return
        self._show_inventory_dialog(item)

    def _void_selected_item(self) -> None:
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "作废余料", "请先选择一条余料。")
            return
        item_id = int(item["id"])
        if QMessageBox.question(self, "作废余料", f"确认作废余料 #{item_id}？") != QMessageBox.StandardButton.Yes:
            return
        self._run_api(
            "正在作废余料...",
            lambda: self.client.void_inventory_item(item_id),
            self._after_inventory_changed,
        )

    def _on_user_loaded(self, user: Mapping[str, Any]) -> None:
        self.current_user = user
        self.request_state_label.setText("已读取当前用户")
        self._refresh_connection_labels()

    def _on_materials_loaded(self, materials: list[Mapping[str, Any]]) -> None:
        self.materials = materials
        self.request_state_label.setText(f"已加载 {len(materials)} 条材质")

    def _on_inventory_loaded(self, items: list[Mapping[str, Any]]) -> None:
        self.inventory_items = items
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.get("id"),
                item.get("materialGrade"),
                item.get("thickness"),
                item.get("width"),
                item.get("length"),
                item.get("quantity"),
                item.get("source"),
                item.get("location"),
                STATUS_LABELS.get(str(item.get("status")), item.get("status")),
                "是" if item.get("reusable") else "否",
                "余料" if item.get("inventoryType") == "leftover" else "整板",
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem("" if value is None else str(value))
                table_item.setData(256, item)
                self.table.setItem(row, col, table_item)
        self.table.resizeColumnsToContents()
        self.request_state_label.setText(f"已加载 {len(items)} 条余料")

    def _after_create_material(self, _material: Mapping[str, Any]) -> None:
        self.request_state_label.setText("材质已新增")
        self.refresh_all()

    def _after_inventory_changed(self, _item: Mapping[str, Any]) -> None:
        self.request_state_label.setText("余料已更新")
        self.refresh_inventory()

    def _run_api(self, status: str, call: Callable[[], Any], on_success: Callable[[Any], None]) -> None:
        if not self.auth_session.can_use_remote_features:
            message = "当前为离线登录，无法使用远程余料管理功能。"
            self.request_state_label.setText(message)
            QMessageBox.information(self, "远程功能不可用", message)
            return
        self.request_state_label.setText(status)
        thread = QThread(self)
        worker = ApiCallWorker(call)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(on_success)
        worker.failed.connect(self._on_api_failed)
        worker.done.connect(thread.quit)
        worker.done.connect(worker.deleteLater)
        thread.finished.connect(lambda: self._threads.remove(thread) if thread in self._threads else None)
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()

    def _on_api_failed(self, message: str) -> None:
        self.request_state_label.setText(message)
        self._refresh_connection_labels()
        QMessageBox.warning(self, "远程请求失败", message)

    def _inventory_query(self) -> dict[str, Any]:
        query: dict[str, Any] = {
            "inventoryType": "leftover",
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
        return table_item.data(256)

    def _refresh_connection_labels(self) -> None:
        self.api_url_label.setText(self.settings.remote_api.base_url or "未配置")
        can_use_remote = self.auth_session.can_use_remote_features
        self.login_state_label.setText("后端账号已登录" if can_use_remote else "离线登录，远程功能禁用")
        if self.current_user:
            display_name = self.current_user.get("displayName") or self.current_user.get("username")
            self.user_label.setText(str(display_name))
        else:
            self.user_label.setText(self.auth_session.display_name or self.auth_session.username)
        self.refresh_btn.setEnabled(can_use_remote)
        self.add_material_btn.setEnabled(can_use_remote)
        self.add_item_btn.setEnabled(can_use_remote)
        self.edit_item_btn.setEnabled(can_use_remote)
        self.void_item_btn.setEnabled(can_use_remote)

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
    def _select_material(combo: QComboBox, material_id: int) -> None:
        for index in range(combo.count()):
            material = combo.itemData(index)
            if material and int(material.get("id", 0)) == material_id:
                combo.setCurrentIndex(index)
                return
