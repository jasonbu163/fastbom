import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config import AppSettings
from gui.main_window import MainWindow
from utils.platform_capabilities import PlatformCapabilities


class MainWindowCapabilitiesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_solidworks_button_disabled_when_local_processing_unavailable(self):
        reason = "此功能需要 Windows + SolidWorks + pywin32 环境。"
        window = MainWindow(
            settings=AppSettings(),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason=reason,
            ),
        )

        self.assertFalse(window.local_processing_page.classify_convert_btn.isEnabled())
        self.assertEqual(window.local_processing_page.classify_convert_btn.toolTip(), reason)


if __name__ == "__main__":
    unittest.main()
