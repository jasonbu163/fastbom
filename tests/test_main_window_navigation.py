import os
import unittest
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication

from auth import AuthSession
from config import AppSettings, InMemorySettingsStore
from config.app_metadata import window_title_with_version
from gui.main_window import MainWindow
from utils.platform_capabilities import PlatformCapabilities


class MainWindowNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_main_window_uses_sidebar_page_model(self):
        window = MainWindow(
            settings=AppSettings(),
            settings_store=InMemorySettingsStore(),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
            ),
        )

        self.assertEqual(window.primary_sidebar.objectName(), "primarySidebar")
        self.assertEqual(window.windowTitle(), window_title_with_version())
        self.assertEqual(window.content_card.objectName(), "contentCard")
        self.assertEqual(window.sidebar.count(), 4)
        self.assertEqual(window.sidebar.item(0).text(), "板材物料库存管理")
        self.assertEqual(window.sidebar.item(1).text(), "本地处理")
        self.assertEqual(window.sidebar.item(2).text(), "用户管理")
        self.assertEqual(window.sidebar.item(3).text(), "设置")
        self.assertEqual(window.pages.count(), 4)

        window.sidebar.setCurrentRow(0)
        self.assertEqual(window.pages.currentWidget(), window.residual_material_page)
        window.sidebar.setCurrentRow(1)
        self.assertEqual(window.pages.currentWidget(), window.local_processing_page)
        window.sidebar.setCurrentRow(2)
        self.assertEqual(window.pages.currentWidget(), window.user_management_page)
        window.sidebar.setCurrentRow(3)
        self.assertEqual(window.pages.currentWidget(), window.settings_page)

    def test_backend_session_logs_out_on_close(self):
        client = Mock()
        window = MainWindow(
            settings=AppSettings(),
            settings_store=InMemorySettingsStore(),
            auth_session=AuthSession.backend_user(
                username="operator",
                access_token="access-token",
                refresh_token="refresh-token",
            ),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
            ),
            remote_api_client_factory=lambda _config: client,
        )

        window.closeEvent(QCloseEvent())

        client.set_session.assert_called_once()
        client.logout.assert_called_once_with()

    def test_offline_session_does_not_logout_on_close(self):
        client_factory = Mock()
        window = MainWindow(
            settings=AppSettings(),
            settings_store=InMemorySettingsStore(),
            auth_session=AuthSession.fallback_admin("admin"),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
            ),
            remote_api_client_factory=client_factory,
        )

        window.closeEvent(QCloseEvent())

        client_factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
