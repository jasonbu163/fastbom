from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from config.settings import (
    AppSettings,
    InMemorySettingsStore,
    save_settings,
)


class SettingsPage(QWidget):
    settings_saved = Signal(AppSettings)

    def __init__(self, settings: AppSettings, store=None):
        super().__init__()
        self.settings = settings
        self.store = store or InMemorySettingsStore()

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(14)

        title = QLabel("设置")
        title.setStyleSheet("font-size: 22px; font-weight: 700;")
        content_layout.addWidget(title)

        self._create_bom_group(content_layout)
        self._create_output_group(content_layout)
        self._create_solidworks_group(content_layout)
        self._create_dxf_group(content_layout)
        self._create_auth_group(content_layout)

        actions = QHBoxLayout()
        actions.addStretch()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self.save_current_settings)
        actions.addWidget(save_btn)
        content_layout.addLayout(actions)
        content_layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _create_bom_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.part_column_edit = QLineEdit(self.settings.bom.part_column)
        self.material_column_edit = QLineEdit(self.settings.bom.material_column)
        self.quantity_column_edit = QLineEdit(self.settings.bom.quantity_column)
        form.addRow("图号列", self.part_column_edit)
        form.addRow("材料列", self.material_column_edit)
        form.addRow("数量列", self.quantity_column_edit)
        layout.addWidget(self._group("BOM", form))

    def _create_output_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.result_dir_edit = QLineEdit(self.settings.output.result_dir)
        self.classified_dir_edit = QLineEdit(self.settings.output.classified_dir)
        self.processed_dxf_dir_edit = QLineEdit(self.settings.output.processed_dxf_dir)
        self.merged_dir_edit = QLineEdit(self.settings.output.merged_dir)
        form.addRow("结果目录", self.result_dir_edit)
        form.addRow("分类目录", self.classified_dir_edit)
        form.addRow("DXF处理目录", self.processed_dxf_dir_edit)
        form.addRow("合并目录", self.merged_dir_edit)
        layout.addWidget(self._group("输出目录", form))

    def _create_solidworks_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.template_dir_edit = QLineEdit(self.settings.solidworks.template_dir)
        self.solidworks_visible_check = QCheckBox("启动新实例时显示 SolidWorks")
        self.solidworks_visible_check.setChecked(self.settings.solidworks.visible)
        form.addRow("模板目录", self.template_dir_edit)
        form.addRow("可见性", self.solidworks_visible_check)
        layout.addWidget(self._group("SolidWorks", form))

    def _create_dxf_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.dxf_text_layer_edit = QLineEdit(self.settings.dxf.text_layer)
        self.dxf_text_color_spin = QSpinBox()
        self.dxf_text_color_spin.setRange(0, 255)
        self.dxf_text_color_spin.setValue(self.settings.dxf.text_color)
        self.dxf_text_height_spin = QDoubleSpinBox()
        self.dxf_text_height_spin.setRange(1.0, 10000.0)
        self.dxf_text_height_spin.setValue(self.settings.dxf.text_height)
        self.dxf_spacing_spin = QDoubleSpinBox()
        self.dxf_spacing_spin.setRange(0.0, 100000.0)
        self.dxf_spacing_spin.setValue(self.settings.dxf.spacing)
        form.addRow("文字图层", self.dxf_text_layer_edit)
        form.addRow("文字颜色", self.dxf_text_color_spin)
        form.addRow("文字高度", self.dxf_text_height_spin)
        form.addRow("合并间距", self.dxf_spacing_spin)
        layout.addWidget(self._group("DXF", form))

    def _create_auth_group(self, layout: QVBoxLayout) -> None:
        form = QFormLayout()
        self.admin_username_label = QLabel(self.settings.auth.fallback_admin_username)
        self.admin_password_edit = QLineEdit()
        self.admin_password_edit.setPlaceholderText("留空则不修改离线密码")
        self.admin_password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("离线账号", self.admin_username_label)
        form.addRow("新离线密码", self.admin_password_edit)
        layout.addWidget(self._group("离线登录", form))

    def save_current_settings(self, show_message: bool = True) -> AppSettings:
        offline_password = self.admin_password_edit.text()
        self.settings = AppSettings(
            app=self.settings.app,
            bom=replace(
                self.settings.bom,
                part_column=self.part_column_edit.text().strip(),
                material_column=self.material_column_edit.text().strip(),
                quantity_column=self.quantity_column_edit.text().strip(),
            ),
            output=replace(
                self.settings.output,
                result_dir=self.result_dir_edit.text().strip(),
                classified_dir=self.classified_dir_edit.text().strip(),
                processed_dxf_dir=self.processed_dxf_dir_edit.text().strip(),
                merged_dir=self.merged_dir_edit.text().strip(),
            ),
            solidworks=replace(
                self.settings.solidworks,
                template_dir=self.template_dir_edit.text().strip(),
                visible=self.solidworks_visible_check.isChecked(),
            ),
            dxf=replace(
                self.settings.dxf,
                text_layer=self.dxf_text_layer_edit.text().strip(),
                text_color=self.dxf_text_color_spin.value(),
                text_height=self.dxf_text_height_spin.value(),
                spacing=self.dxf_spacing_spin.value(),
            ),
            remote_api=self.settings.remote_api,
            auth=replace(
                self.settings.auth,
                fallback_admin_username="admin",
                fallback_admin_password=offline_password or self.settings.auth.fallback_admin_password,
            ),
        )
        save_settings(self.settings, self.store)
        self.admin_password_edit.clear()
        self.settings_saved.emit(self.settings)
        if show_message:
            QMessageBox.information(self, "设置", "设置已保存，部分设置将在重启后生效。")
        return self.settings

    @staticmethod
    def _group(title: str, layout: QFormLayout) -> QGroupBox:
        group = QGroupBox(title)
        group.setLayout(layout)
        return group
