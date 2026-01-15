# utils/show.py
import ctypes
from PySide6.QtWidgets import QMessageBox


class Show:
    """消息提示工具"""
    @staticmethod
    def win32_message_box(title, msg, icon = 0):
        ctypes.windll.user32.MessageBoxW(0, msg, title, icon)
    
    @staticmethod
    def message_box(title: str, message: str, icon_type: int = 64):
        """
        显示消息框
        
        Args:
            title: 标题
            message: 消息内容
            icon_type: 图标类型 (16=错误, 48=警告, 64=信息)
        """
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        
        if icon_type == 16:
            msg_box.setIcon(QMessageBox.Icon.Critical)
        elif icon_type == 48:
            msg_box.setIcon(QMessageBox.Icon.Warning)
        else:
            msg_box.setIcon(QMessageBox.Icon.Information)
        
        msg_box.exec()