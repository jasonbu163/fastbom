# main.py
import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from config import QtSettingsStore, load_settings
from gui.login_dialog import LoginDialog
from gui.main_window import MainWindow
from services.auth_service import AuthService


def main():
    """主函数"""
    app = QApplication(sys.argv)
    settings_store = QtSettingsStore()
    settings = load_settings(store=settings_store)
    
    apply_stylesheet(app, theme=settings.app.theme)

    login_dialog = LoginDialog(AuthService(settings), settings=settings, settings_store=settings_store)
    if login_dialog.exec() != LoginDialog.DialogCode.Accepted or login_dialog.auth_session is None:
        sys.exit(0)
    settings = login_dialog.settings
    
    window = MainWindow(
        settings=settings,
        settings_store=settings_store,
        auth_session=login_dialog.auth_session,
    )
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
