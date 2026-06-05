# main.py
import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from config import QtSettingsStore, load_settings
from gui.main_window import MainWindow


def main():
    """主函数"""
    app = QApplication(sys.argv)
    settings_store = QtSettingsStore()
    settings = load_settings(store=settings_store)
    
    apply_stylesheet(app, theme=settings.app.theme)
    
    window = MainWindow(settings=settings, settings_store=settings_store)
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
