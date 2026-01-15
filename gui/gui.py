# gui.py
import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QTextEdit,
    QFileDialog, QGroupBox, QProgressBar, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon


class BatchProcessThread(QThread):
    """后台处理线程"""
    progress = Signal(int, int)  # 当前进度, 总数
    log = Signal(str)  # 日志消息
    finished = Signal(int, int)  # 成功数, 失败数
    
    def __init__(self, directory, recursive=False):
        super().__init__()
        self.directory = directory
        self.recursive = recursive
        self.is_running = True
    
    def run(self):
        """在后台线程中执行批处理"""
        import pythoncom
        pythoncom.CoInitialize()
        
        try:
            from run import get_sw_app, batch_process_solidworks
            
            self.log.emit("正在连接 SolidWorks...")
            sw_app = get_sw_app()
            
            self.log.emit(f"目标目录: {self.directory}")
            
            # 这里需要修改 batch_process_solidworks 来支持进度回调
            # 暂时简化处理
            from run import get_solidworks_files, process_single_file
            
            files = get_solidworks_files(self.directory, extensions=['.SLDDRW'])
            
            if not files:
                self.log.emit("未找到工程图文件！")
                self.finished.emit(0, 0)
                return
            
            self.log.emit(f"找到 {len(files)} 个文件")
            
            success = 0
            failed = 0
            
            for i, filepath in enumerate(files, 1):
                if not self.is_running:
                    self.log.emit("用户取消处理")
                    break
                
                self.log.emit(f"[{i}/{len(files)}] {os.path.basename(filepath)}")
                self.progress.emit(i, len(files))
                
                if process_single_file(sw_app, filepath):
                    success += 1
                    self.log.emit("  ✓ 成功")
                else:
                    failed += 1
                    self.log.emit("  ✗ 失败")
            
            self.finished.emit(success, failed)
            
        except Exception as e:
            self.log.emit(f"错误: {e}")
            import traceback
            self.log.emit(traceback.format_exc())
        
        finally:
            pythoncom.CoUninitialize()
    
    def stop(self):
        """停止处理"""
        self.is_running = False


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.thread = None
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        self.setWindowTitle("SolidWorks 批量处理工具")
        self.setMinimumSize(800, 600)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        # title = QLabel("SolidWorks 工程图批量处理")
        # title_font = QFont()
        # title_font.setPointSize(16)
        # title_font.setBold(True)
        # title.setFont(title_font)
        # title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # layout.addWidget(title)
        
        # 目录选择组
        dir_group = QGroupBox("选择目录")
        dir_layout = QHBoxLayout()
        
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("请选择包含工程图的目录...")
        self.dir_input.setReadOnly(True)
        
        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.clicked.connect(self.browse_directory)
        
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        dir_group.setLayout(dir_layout)
        layout.addWidget(dir_group)
        
        # 选项组
        options_group = QGroupBox("处理选项")
        options_layout = QVBoxLayout()
        
        self.recursive_check = QCheckBox("包含子目录")
        self.recursive_check.setChecked(False)
        options_layout.addWidget(self.recursive_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # 日志输出
        log_group = QGroupBox("处理日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("开始处理")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        
        self.clear_btn = QPushButton("清除日志")
        self.clear_btn.clicked.connect(self.log_text.clear)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # 设置默认目录
        default_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "source_file"
        )
        if os.path.exists(default_dir):
            self.dir_input.setText(default_dir)
            self.start_btn.setEnabled(True)
    
    def browse_directory(self):
        """浏览选择目录"""
        current_dir = self.dir_input.text()
        if not current_dir or not os.path.exists(current_dir):
            current_dir = os.path.dirname(os.path.abspath(__file__))
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择包含工程图的目录",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self.dir_input.setText(directory)
            self.start_btn.setEnabled(True)
            self.append_log(f"选择目录: {directory}")
    
    def start_processing(self):
        """开始处理"""
        directory = self.dir_input.text()
        
        if not directory or not os.path.exists(directory):
            QMessageBox.warning(self, "警告", "请选择有效的目录！")
            return
        
        # 禁用控制
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.recursive_check.setEnabled(False)
        
        # 清空日志和进度
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # 创建并启动线程
        self.thread = BatchProcessThread(
            directory,
            self.recursive_check.isChecked()
        )
        self.thread.progress.connect(self.update_progress)
        self.thread.log.connect(self.append_log)
        self.thread.finished.connect(self.processing_finished)
        self.thread.start()
        
        self.append_log("开始批量处理...")
    
    def stop_processing(self):
        """停止处理"""
        if self.thread and self.thread.isRunning():
            self.append_log("正在停止...")
            self.thread.stop()
            self.thread.wait()
    
    def update_progress(self, current, total):
        """更新进度条"""
        progress = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
    
    def append_log(self, message):
        """添加日志"""
        self.log_text.append(message)
        # 自动滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )
    
    def processing_finished(self, success, failed):
        """处理完成"""
        total = success + failed
        self.append_log("=" * 60)
        self.append_log(f"处理完成！成功: {success}, 失败: {failed}, 总计: {total}")
        self.append_log("=" * 60)
        
        # 恢复控制
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)
        self.recursive_check.setEnabled(True)
        
        # 显示完成对话框
        QMessageBox.information(
            self,
            "完成",
            f"批量处理已完成！\n\n成功: {success}\n失败: {failed}\n总计: {total}"
        )


def main():
    """启动GUI"""
    from qt_material import apply_stylesheet

    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_teal.xml")

    # 设置本地图标
    icon = QIcon("static/repair_home_improvement_tools_construction_hammer_icon_267272.ico")

    window = MainWindow()
    window.setWindowIcon(icon)
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()