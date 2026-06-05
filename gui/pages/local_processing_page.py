from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import AppSettings
from core import BOMClassifier
from gui.worker_thread import WorkerThread
from utils.platform_capabilities import PlatformCapabilities, detect_platform_capabilities


class LocalProcessingPage(QWidget):
    def __init__(
        self,
        settings: AppSettings,
        platform_capabilities: Optional[PlatformCapabilities] = None,
    ):
        super().__init__()
        self.settings = settings
        self.platform_capabilities = platform_capabilities or detect_platform_capabilities()
        self.classifier = BOMClassifier(output_config=self.settings.output)
        self.config: Dict[str, str] = {
            "part": self.settings.bom.part_column,
            "mat": self.settings.bom.material_column,
            "qty": self.settings.bom.quantity_column,
        }
        self.worker: Optional[WorkerThread] = None
        self.classify_output_dir: Optional[Path] = None
        self.processed_dxf_output_dir: Optional[Path] = None
        self.merged_dxf_output_dir: Optional[Path] = None

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(16)

        self.local_pages = QStackedWidget()
        root_layout.addWidget(self.local_pages, 1)

        nav_card = QFrame()
        nav_card.setObjectName("secondaryNavCard")
        nav_layout = QVBoxLayout(nav_card)
        nav_layout.setContentsMargins(14, 14, 14, 14)
        nav_layout.setSpacing(10)

        nav_title = QLabel("本地处理导航")
        nav_title.setObjectName("secondaryNavTitle")
        nav_layout.addWidget(nav_title)

        self.local_nav = QListWidget()
        self.local_nav.setObjectName("secondaryNav")
        self.local_nav.addItem("准备与识别")
        self.local_nav.addItem("分类转换")
        self.local_nav.addItem("DXF 标注")
        self.local_nav.addItem("DXF 合并")
        nav_layout.addWidget(self.local_nav, 1)
        nav_card.setFixedWidth(210)
        root_layout.addWidget(nav_card)

        self.local_pages.addWidget(self._create_prepare_page())
        self.local_pages.addWidget(self._create_convert_page())
        self.local_pages.addWidget(self._create_dxf_mark_page())
        self.local_pages.addWidget(self._create_dxf_merge_page())
        self.local_nav.currentRowChanged.connect(self.local_pages.setCurrentIndex)
        self.local_nav.setCurrentRow(0)

    def update_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        self.config = {
            "part": self.settings.bom.part_column,
            "mat": self.settings.bom.material_column,
            "qty": self.settings.bom.quantity_column,
        }
        self.classifier.output_config = self.settings.output

    def _page_shell(self) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setObjectName("workflowScroll")
        scroll.setWidgetResizable(True)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_widget = QWidget()
        scroll_widget.setObjectName("workflowScrollContent")
        scroll_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(scroll_widget)
        page_layout.addWidget(scroll)
        return page, scroll_layout

    def _create_prepare_page(self) -> QWidget:
        page, layout = self._page_shell()
        self._create_step1(layout)
        self._create_step2(layout)
        layout.addStretch()
        return page

    def _create_convert_page(self) -> QWidget:
        page, layout = self._page_shell()
        self._create_step3(layout, expand=True)
        return page

    def _create_dxf_mark_page(self) -> QWidget:
        page, layout = self._page_shell()
        self._create_step4(layout, expand=True)
        return page

    def _create_dxf_merge_page(self) -> QWidget:
        page, layout = self._page_shell()
        self._create_step5(layout, expand=True)
        return page

    def _step_card(self, title: str, expand: bool = False) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("stepCard")
        if expand:
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 18)
        card_layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("stepTitle")
        card_layout.addWidget(title_label)
        return card, card_layout

    def _create_log_actions(
        self,
        log_widget: QTextEdit,
        default_filename: str,
        output_dir_attr: str,
    ) -> tuple[QHBoxLayout, QPushButton, QPushButton]:
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()

        save_log_btn = QPushButton("保存当前日志")
        save_log_btn.clicked.connect(lambda: self._save_log(log_widget, default_filename))
        actions_layout.addWidget(save_log_btn)

        open_dir_btn = QPushButton("打开所在目录")
        open_dir_btn.setEnabled(False)
        open_dir_btn.clicked.connect(lambda: self._open_output_dir(output_dir_attr))
        actions_layout.addWidget(open_dir_btn)

        return actions_layout, save_log_btn, open_dir_btn

    def _create_step1(self, layout: QVBoxLayout) -> None:
        group, group_layout = self._step_card("第一步：选择项目目录")

        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("项目目录:"))
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setReadOnly(True)
        self.project_path_edit.setPlaceholderText("请选择包含BOM表和SLDDRW文件的项目目录...")
        dir_layout.addWidget(self.project_path_edit)

        dir_btn = QPushButton("选择项目目录")
        dir_btn.setMaximumWidth(150)
        dir_btn.clicked.connect(self._select_project_dir)
        dir_layout.addWidget(dir_btn)

        info = QLabel(
            "提示：\n"
            "  • 请将BOM表（Excel）和工程图文件（SLDDRW）放在同一目录下\n"
            "  • 处理结果将保存在该目录下的 'result' 文件夹中"
        )
        info.setObjectName("hintLabel")

        group_layout.addLayout(dir_layout)
        group_layout.addWidget(info)
        layout.addWidget(group)

    def _create_step2(self, layout: QVBoxLayout) -> None:
        group, group_layout = self._step_card("第二步：智能识别BOM表和工程图")

        bom_layout = QHBoxLayout()
        bom_layout.addWidget(QLabel("BOM表:"))
        self.bom_combo = QComboBox()
        self.bom_combo.setPlaceholderText("选择项目目录后自动识别...")
        bom_layout.addWidget(self.bom_combo)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self._refresh_bom_list)
        bom_layout.addWidget(refresh_btn)

        self.status_label = QLabel("等待选择项目目录...")
        self.header_label = QLabel("")

        group_layout.addLayout(bom_layout)
        group_layout.addWidget(self.status_label)
        group_layout.addWidget(self.header_label)
        layout.addWidget(group)

    def _create_step3(self, layout: QVBoxLayout, expand: bool = False) -> None:
        group, group_layout = self._step_card("第三步：智能分类 + DXF转换（一键完成）", expand)

        local_processing_note = ""
        if not self.platform_capabilities.solidworks_local_processing_available:
            local_processing_note = f"\n  当前环境不可用：{self.platform_capabilities.solidworks_local_processing_reason}"

        info = QLabel(
            "功能：自动处理工程图并分类归档\n"
            "  1. 根据BOM表查找对应的工程图文件\n"
            "  2. 调用SolidWorks转换为DXF格式\n"
            f"  3. 按材料和厚度自动分类存储{local_processing_note}"
        )
        info.setObjectName("hintLabel")

        self.classify_convert_btn = QPushButton("开始智能处理")
        self.classify_convert_btn.clicked.connect(self._on_classify_and_convert)
        if not self.platform_capabilities.solidworks_local_processing_available:
            self.classify_convert_btn.setEnabled(False)
            self.classify_convert_btn.setToolTip(self.platform_capabilities.solidworks_local_processing_reason)

        self.progress1 = QProgressBar()
        self.log1 = QTextEdit()
        self.log1.setReadOnly(True)
        self.log1.setMinimumHeight(260)
        actions_layout, self.save_log1_btn, self.open_classify_dir_btn = self._create_log_actions(
            self.log1,
            "fastbom-classify-convert.log",
            "classify_output_dir",
        )

        group_layout.addWidget(info)
        group_layout.addWidget(self.classify_convert_btn)
        group_layout.addWidget(self.progress1)
        group_layout.addWidget(self.log1, 1)
        group_layout.addLayout(actions_layout)
        layout.addWidget(group, 1 if expand else 0)

    def _create_step4(self, layout: QVBoxLayout, expand: bool = False) -> None:
        group, group_layout = self._step_card("第四步：DXF智能标注", expand)

        info = QLabel("功能：在图层0下方添加文件名标注")
        info.setObjectName("hintLabel")

        btn = QPushButton("开始处理DXF文件")
        btn.clicked.connect(self._on_process_dxf)

        self.progress2 = QProgressBar()
        self.log2 = QTextEdit()
        self.log2.setReadOnly(True)
        self.log2.setMinimumHeight(260)
        actions_layout, self.save_log2_btn, self.open_processed_dxf_dir_btn = self._create_log_actions(
            self.log2,
            "fastbom-dxf-annotation.log",
            "processed_dxf_output_dir",
        )

        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress2)
        group_layout.addWidget(self.log2, 1)
        group_layout.addLayout(actions_layout)
        layout.addWidget(group, 1 if expand else 0)

    def _create_step5(self, layout: QVBoxLayout, expand: bool = False) -> None:
        group, group_layout = self._step_card("第五步：按材料/厚度合并DXF", expand)

        info = QLabel("功能：将同材料、同厚度的DXF文件合并到一个文件")
        info.setObjectName("hintLabel")

        btn = QPushButton("开始合并DXF文件")
        btn.clicked.connect(self._on_merge_dxf)

        self.progress3 = QProgressBar()
        self.log3 = QTextEdit()
        self.log3.setReadOnly(True)
        self.log3.setMinimumHeight(260)
        actions_layout, self.save_log3_btn, self.open_merged_dxf_dir_btn = self._create_log_actions(
            self.log3,
            "fastbom-dxf-merge.log",
            "merged_dxf_output_dir",
        )

        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress3)
        group_layout.addWidget(self.log3, 1)
        group_layout.addLayout(actions_layout)
        layout.addWidget(group, 1 if expand else 0)

    def _save_log(self, log_widget: QTextEdit, default_filename: str) -> None:
        log_text = log_widget.toPlainText().strip()
        if not log_text:
            QMessageBox.information(self, "提示", "当前没有可保存的日志")
            return

        default_dir = self.classifier.result_dir or self.classifier.project_dir or Path.home()
        default_path = default_dir / default_filename
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存当前日志",
            str(default_path),
            "Log Files (*.log);;Text Files (*.txt);;All Files (*)",
        )
        if not file_path:
            return

        try:
            Path(file_path).write_text(f"{log_text}\n", encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, "保存失败", f"无法保存日志：{exc}")
            return

        QMessageBox.information(self, "保存完成", f"日志已保存到：\n{file_path}")

    def _open_output_dir(self, output_dir_attr: str) -> None:
        output_dir = getattr(self, output_dir_attr, None)
        if not output_dir:
            QMessageBox.information(self, "提示", "当前还没有可打开的输出目录")
            return

        if not output_dir.exists():
            QMessageBox.warning(self, "提示", f"输出目录不存在：\n{output_dir}")
            return

        self.classifier.open_folder(output_dir)

    def _select_project_dir(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录（包含BOM表和SLDDRW文件）",
            "",
        )

        if dir_path:
            if self.classifier.set_project_dir(dir_path):
                self.project_path_edit.setText(dir_path)
                self._refresh_bom_list()
                bom_files = self.classifier.find_bom_files()
                slddrw_files = self.classifier.find_slddrw_files()
                self.status_label.setText(
                    f"项目目录已设置\n"
                    f"   找到 {len(bom_files)} 个Excel文件\n"
                    f"   找到 {len(slddrw_files)} 个工程图文件"
                )
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                QMessageBox.warning(self, "错误", "无效的目录路径")

    def _refresh_bom_list(self) -> None:
        self.bom_combo.clear()

        if not self.classifier.project_dir:
            return

        bom_files = self.classifier.find_bom_files()
        if not bom_files:
            self.bom_combo.addItem("未找到Excel文件")
            return

        for bom_file in bom_files:
            self.bom_combo.addItem(bom_file.name, str(bom_file))

        if len(bom_files) == 1:
            self.bom_combo.setCurrentIndex(0)
            self._load_selected_bom()

        self.bom_combo.currentIndexChanged.connect(self._load_selected_bom)

    def _load_selected_bom(self) -> None:
        bom_path = self.bom_combo.currentData()
        if not bom_path:
            return

        if self.classifier.set_bom_file(bom_path):
            success, msg = self.classifier.load_bom_headers()
            self.header_label.setText(msg)
            if success:
                self.header_label.setStyleSheet("color: green;")
                headers_text = f"检测到的列: {', '.join(self.classifier.headers[:5])}"
                if len(self.classifier.headers) > 5:
                    headers_text += "..."
                self.header_label.setText(f"{msg}\n{headers_text}")
            else:
                self.header_label.setStyleSheet("color: orange;")

    def _on_classify_and_convert(self) -> None:
        if not self.classifier.bom_file:
            QMessageBox.warning(self, "提示", "请先选择BOM表")
            return

        if not self.classifier.project_dir:
            QMessageBox.warning(self, "提示", "请先选择项目目录")
            return

        reply = QMessageBox.question(
            self,
            "确认",
            "即将启动SolidWorks进行批量转换，这可能需要较长时间。\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.log1.clear()
        self.progress1.setValue(0)
        self.classify_output_dir = None
        self.open_classify_dir_btn.setEnabled(False)

        self.worker = WorkerThread("classify_and_convert", self.classifier, self.config, self.settings)
        self.worker.progress.connect(self.progress1.setValue)
        self.worker.log_message.connect(lambda msg: self.log1.append(msg))
        self.worker.finished.connect(self._on_classify_finished)
        self.worker.start()

    def _on_classify_finished(self, success: bool, msg: str) -> None:
        if success and self.classifier.classified_dir:
            self.classify_output_dir = self.classifier.classified_dir
            self.open_classify_dir_btn.setEnabled(True)
            QMessageBox.information(self, "完成", msg)
        else:
            QMessageBox.warning(self, "失败", msg)

    def _on_process_dxf(self) -> None:
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "请先完成智能处理（步骤3）")
            return

        self.log2.clear()
        self.progress2.setValue(0)
        self.processed_dxf_output_dir = None
        self.open_processed_dxf_dir_btn.setEnabled(False)

        self.worker = WorkerThread("process_dxf", self.classifier, self.config, self.settings)
        self.worker.progress.connect(self.progress2.setValue)
        self.worker.log_message.connect(lambda msg: self.log2.append(msg))
        self.worker.finished.connect(self._on_process_dxf_finished)
        self.worker.start()

    def _on_process_dxf_finished(self, success: bool, msg: str) -> None:
        if success and self.classifier.processed_dxf_dir:
            self.processed_dxf_output_dir = self.classifier.processed_dxf_dir
            self.open_processed_dxf_dir_btn.setEnabled(True)
            QMessageBox.information(self, "完成", msg)
        else:
            QMessageBox.warning(self, "失败", msg)

    def _on_merge_dxf(self) -> None:
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "请先完成智能处理（步骤3）")
            return

        self.log3.clear()
        self.progress3.setValue(0)
        self.merged_dxf_output_dir = None
        self.open_merged_dxf_dir_btn.setEnabled(False)

        self.worker = WorkerThread("merge_dxf", self.classifier, app_settings=self.settings)
        self.worker.log_message.connect(lambda msg: self.log3.append(msg))
        self.worker.finished.connect(self._on_merge_dxf_finished)
        self.worker.start()

    def _on_merge_dxf_finished(self, success: bool, msg: str) -> None:
        self.progress3.setValue(100)
        if success and self.classifier.merged_dir:
            self.merged_dxf_output_dir = self.classifier.merged_dir
            self.open_merged_dxf_dir_btn.setEnabled(True)
            QMessageBox.information(self, "完成", msg)
        else:
            QMessageBox.warning(self, "失败", msg)
