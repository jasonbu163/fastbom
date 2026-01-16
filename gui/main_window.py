# gui/main_window.py

from typing import Dict, Optional
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QProgressBar, QGroupBox, QMessageBox,
    QScrollArea, QFileDialog, QLineEdit, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon

from core import BOMClassifier
from gui.worker_thread import WorkerThread


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.classifier = BOMClassifier()
        self.config: Dict[str, str] = {'part': '图号', 'mat': '材料', 'qty': '总数量'}
        self.worker: Optional[WorkerThread] = None
        
        self.setWindowTitle("FastBOM智能处理系统 v2.0")
        self.setMinimumSize(900, 700)
        
        # 设置图标（如果存在）
        icon_path = Path("static/efficacy_researching_settings_icon_152066.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 创建滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        
        # 步骤1：选择项目目录
        self._create_step1(scroll_layout)
        
        # 步骤2：智能识别
        self._create_step2(scroll_layout)
        
        # 步骤3：分类和转换（整合）
        self._create_step3(scroll_layout)
        
        # 步骤4：DXF处理
        self._create_step4(scroll_layout)
        
        # 步骤5：DXF合并
        self._create_step5(scroll_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
    
    def _create_step1(self, layout: QVBoxLayout) -> None:
        """步骤1：选择项目目录"""
        group = QGroupBox("第一步：选择项目目录")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        # 项目目录选择
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("项目目录:"))
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setReadOnly(True)
        self.project_path_edit.setPlaceholderText("请选择包含BOM表和SLDDRW文件的项目目录...")
        dir_layout.addWidget(self.project_path_edit)
        
        dir_btn = QPushButton("📁 选择项目目录")
        dir_btn.setMaximumWidth(150)
        dir_btn.clicked.connect(self._select_project_dir)
        dir_layout.addWidget(dir_btn)
        
        # 说明文字
        info = QLabel(
            "💡 提示：\n"
            "  • 请将BOM表（Excel）和工程图文件（SLDDRW）放在同一目录下\n"
            "  • 处理结果将保存在该目录下的 'result' 文件夹中"
        )
        info.setStyleSheet("color: #c2c2c2; padding: 10px;")
        
        group_layout.addLayout(dir_layout)
        group_layout.addWidget(info)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step2(self, layout: QVBoxLayout) -> None:
        """步骤2：智能识别"""
        group = QGroupBox("第二步：智能识别BOM表和工程图")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        # BOM文件选择（自动/手动）
        bom_layout = QHBoxLayout()
        bom_layout.addWidget(QLabel("BOM表:"))
        self.bom_combo = QComboBox()
        self.bom_combo.setPlaceholderText("选择项目目录后自动识别...")
        bom_layout.addWidget(self.bom_combo)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self._refresh_bom_list)
        bom_layout.addWidget(refresh_btn)
        
        # 状态显示
        self.status_label = QLabel("等待选择项目目录...")
        self.status_label.setFont(QFont("Arial", 11))
        
        # 表头显示
        self.header_label = QLabel("")
        self.header_label.setFont(QFont("Arial", 10))
        
        group_layout.addLayout(bom_layout)
        group_layout.addWidget(self.status_label)
        group_layout.addWidget(self.header_label)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step3(self, layout: QVBoxLayout) -> None:
        """步骤3：智能分类和转换（整合）"""
        group = QGroupBox("第三步：智能分类 + DXF转换（一键完成）")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        info = QLabel(
            "功能：自动处理工程图并分类归档\n"
            "  1. 根据BOM表查找对应的工程图文件\n"
            "  2. 调用SolidWorks转换为DXF格式\n"
            "  3. 按材料和厚度自动分类存储"
        )
        info.setStyleSheet("color: #c2c2c2; padding: 10px;")
        
        btn = QPushButton("🚀 开始智能处理")
        btn.clicked.connect(self._on_classify_and_convert)
        
        self.progress1 = QProgressBar()
        
        self.log1 = QTextEdit()
        self.log1.setReadOnly(True)
        self.log1.setMinimumHeight(300) # set log minimum height
        
        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress1)
        group_layout.addWidget(self.log1)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step4(self, layout: QVBoxLayout) -> None:
        """步骤4：DXF处理"""
        group = QGroupBox("第四步：DXF智能标注")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        info = QLabel("功能：在图层0下方添加文件名标注")
        info.setStyleSheet("color: #c2c2c2; padding: 10px;")
        
        btn = QPushButton("🎨 开始处理DXF文件")
        btn.clicked.connect(self._on_process_dxf)
        
        self.progress2 = QProgressBar()
        
        self.log2 = QTextEdit()
        self.log2.setReadOnly(True)
        self.log2.setMinimumHeight(300)
        
        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress2)
        group_layout.addWidget(self.log2)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_step5(self, layout: QVBoxLayout) -> None:
        """步骤5：DXF合并"""
        group = QGroupBox("第五步：按材料/厚度合并DXF")
        group.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        group_layout = QVBoxLayout()
        
        info = QLabel("功能：将同材料、同厚度的DXF文件合并到一个文件")
        info.setStyleSheet("color: #c2c2c2; padding: 10px;")
        
        btn = QPushButton("🔗 开始合并DXF文件")
        btn.clicked.connect(self._on_merge_dxf)
        
        self.progress3 = QProgressBar()
        
        self.log3 = QTextEdit()
        self.log3.setReadOnly(True)
        self.log3.setMinimumHeight(300)
        
        group_layout.addWidget(info)
        group_layout.addWidget(btn)
        group_layout.addWidget(self.progress3)
        group_layout.addWidget(self.log3)
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _select_project_dir(self) -> None:
        """选择项目目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录（包含BOM表和SLDDRW文件）",
            ""
        )
        
        if dir_path:
            if self.classifier.set_project_dir(dir_path):
                self.project_path_edit.setText(dir_path)
                
                # 自动刷新BOM列表
                self._refresh_bom_list()
                
                # 检测文件
                bom_files = self.classifier.find_bom_files()
                slddrw_files = self.classifier.find_slddrw_files()
                
                self.status_label.setText(
                    f"✅ 项目目录已设置\n"
                    f"   📋 找到 {len(bom_files)} 个Excel文件\n"
                    f"   📐 找到 {len(slddrw_files)} 个工程图文件"
                )
                self.status_label.setStyleSheet("color: green; font-weight: bold;")
            else:
                QMessageBox.warning(self, "错误", "❌ 无效的目录路径")
    
    def _refresh_bom_list(self) -> None:
        """刷新BOM文件列表"""
        self.bom_combo.clear()
        
        if not self.classifier.project_dir:
            return
        
        bom_files = self.classifier.find_bom_files()
        
        if not bom_files:
            self.bom_combo.addItem("未找到Excel文件")
            return
        
        for bom_file in bom_files:
            self.bom_combo.addItem(bom_file.name, str(bom_file))
        
        # 如果只有一个，自动选择并加载
        if len(bom_files) == 1:
            self.bom_combo.setCurrentIndex(0)
            self._load_selected_bom()
        
        # 连接选择信号
        self.bom_combo.currentIndexChanged.connect(self._load_selected_bom)
    
    def _load_selected_bom(self) -> None:
        """加载选中的BOM表"""
        bom_path = self.bom_combo.currentData()
        if not bom_path:
            return
        
        if self.classifier.set_bom_file(bom_path):
            success, msg = self.classifier.load_bom_headers()
            self.header_label.setText(msg)
            if success:
                self.header_label.setStyleSheet("color: green;")
                
                # 显示表头信息
                headers_text = f"检测到的列: {', '.join(self.classifier.headers[:5])}"
                if len(self.classifier.headers) > 5:
                    headers_text += "..."
                self.header_label.setText(f"{msg}\n{headers_text}")
            else:
                self.header_label.setStyleSheet("color: orange;")
    
    def _on_classify_and_convert(self) -> None:
        """启动分类和转换任务"""
        if not self.classifier.bom_file:
            QMessageBox.warning(self, "提示", "⚠️ 请先选择BOM表")
            return
        
        if not self.classifier.project_dir:
            QMessageBox.warning(self, "提示", "⚠️ 请先选择项目目录")
            return
        
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认",
            "即将启动SolidWorks进行批量转换，这可能需要较长时间。\n是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        self.log1.clear()
        self.progress1.setValue(0)
        
        self.worker = WorkerThread("classify_and_convert", self.classifier, self.config)
        self.worker.progress.connect(self.progress1.setValue)
        self.worker.log_message.connect(lambda msg: self.log1.append(msg))
        self.worker.finished.connect(self._on_classify_finished)
        self.worker.start()
    
    def _on_classify_finished(self, success: bool, msg: str) -> None:
        """分类和转换完成"""
        if success and self.classifier.classified_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.classified_dir)
        else:
            QMessageBox.warning(self, "失败", msg)
    
    def _on_process_dxf(self) -> None:
        """启动DXF处理任务"""
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "⚠️ 请先完成智能处理（步骤3）")
            return
        
        self.log2.clear()
        self.progress2.setValue(0)
        
        self.worker = WorkerThread("process_dxf", self.classifier, self.config)
        self.worker.progress.connect(self.progress2.setValue)
        self.worker.log_message.connect(lambda msg: self.log2.append(msg))
        self.worker.finished.connect(self._on_process_dxf_finished)
        self.worker.start()
    
    def _on_process_dxf_finished(self, success: bool, msg: str) -> None:
        """DXF处理完成"""
        if success and self.classifier.processed_dxf_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.processed_dxf_dir)
        else:
            QMessageBox.warning(self, "失败", msg)
    
    def _on_merge_dxf(self) -> None:
        """启动DXF合并任务"""
        if not self.classifier.classified_dir or not self.classifier.classified_dir.exists():
            QMessageBox.warning(self, "提示", "⚠️ 请先完成智能处理（步骤3）")
            return
        
        self.log3.clear()
        self.progress3.setValue(0)
        
        self.worker = WorkerThread("merge_dxf", self.classifier)
        self.worker.log_message.connect(lambda msg: self.log3.append(msg))
        self.worker.finished.connect(self._on_merge_dxf_finished)
        self.worker.start()
    
    def _on_merge_dxf_finished(self, success: bool, msg: str) -> None:
        """DXF合并完成"""
        self.progress3.setValue(100)
        if success and self.classifier.merged_dir:
            QMessageBox.information(self, "完成", msg)
            self.classifier.open_folder(self.classifier.merged_dir)
        else:
            QMessageBox.warning(self, "失败", msg)