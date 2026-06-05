import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config import AppSettings, InMemorySettingsStore
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
        self.assertEqual(window.content_card.objectName(), "contentCard")
        self.assertEqual(window.sidebar.count(), 2)
        self.assertEqual(window.sidebar.item(0).text(), "本地处理")
        self.assertEqual(window.sidebar.item(1).text(), "设置")
        self.assertEqual(window.pages.count(), 2)

        window.sidebar.setCurrentRow(1)
        self.assertEqual(window.pages.currentWidget(), window.settings_page)


if __name__ == "__main__":
    unittest.main()
