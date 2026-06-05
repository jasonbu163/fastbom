import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from config import AppSettings
from gui.pages.local_processing_page import LocalProcessingPage
from utils.platform_capabilities import PlatformCapabilities


class LocalProcessingPageNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_local_processing_page_has_four_secondary_pages(self):
        page = LocalProcessingPage(
            settings=AppSettings(),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
            ),
        )

        self.assertEqual(page.local_nav.count(), 4)
        self.assertEqual(page.local_nav.item(0).text(), "准备与识别")
        self.assertEqual(page.local_nav.item(1).text(), "分类转换")
        self.assertEqual(page.local_nav.item(2).text(), "DXF 标注")
        self.assertEqual(page.local_nav.item(3).text(), "DXF 合并")
        self.assertEqual(page.local_pages.count(), 4)
        self.assertEqual(page.local_pages.currentIndex(), 0)

        page.local_nav.setCurrentRow(3)
        self.assertEqual(page.local_pages.currentIndex(), 3)

    def test_output_directory_buttons_are_manual_after_success(self):
        page = LocalProcessingPage(
            settings=AppSettings(),
            platform_capabilities=PlatformCapabilities(
                platform_name="windows",
                solidworks_local_processing_available=True,
                solidworks_local_processing_reason="",
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            page.classifier.classified_dir = output_dir

            self.assertFalse(page.open_classify_dir_btn.isEnabled())

            with (
                patch.object(QMessageBox, "information"),
                patch.object(page.classifier, "open_folder") as open_folder,
            ):
                page._on_classify_finished(True, "完成")

            self.assertTrue(page.open_classify_dir_btn.isEnabled())
            self.assertEqual(page.classify_output_dir, output_dir)
            open_folder.assert_not_called()

            with patch.object(page.classifier, "open_folder") as open_folder:
                page._open_output_dir("classify_output_dir")

            open_folder.assert_called_once_with(output_dir)

    def test_save_current_log_writes_selected_file(self):
        page = LocalProcessingPage(
            settings=AppSettings(),
            platform_capabilities=PlatformCapabilities(
                platform_name="darwin",
                solidworks_local_processing_available=False,
                solidworks_local_processing_reason="此功能需要 Windows + SolidWorks + pywin32 环境。",
            ),
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "current.log"
            page.log1.setPlainText("line 1\nline 2")

            with (
                patch.object(QFileDialog, "getSaveFileName", return_value=(str(target), "")),
                patch.object(QMessageBox, "information"),
            ):
                page._save_log(page.log1, "default.log")

            self.assertEqual(target.read_text(encoding="utf-8"), "line 1\nline 2\n")


if __name__ == "__main__":
    unittest.main()
