import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from config.settings import AppSettings, InMemorySettingsStore, load_settings
from gui.pages.settings_page import SettingsPage


class SettingsPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_save_persists_edited_settings_to_store(self):
        store = InMemorySettingsStore()
        page = SettingsPage(AppSettings(), store=store)

        page.theme_edit.setText("light_blue.xml")
        page.api_base_url_edit.setText("https://api.example.test")
        page.api_timeout_spin.setValue(30)
        page.part_column_edit.setText("零件号")
        page.solidworks_visible_check.setChecked(True)

        saved_settings = page.save_current_settings(show_message=False)
        loaded_settings = load_settings(store=store)

        self.assertEqual(saved_settings.app.theme, "light_blue.xml")
        self.assertEqual(loaded_settings.remote_api.base_url, "https://api.example.test")
        self.assertEqual(loaded_settings.remote_api.timeout_seconds, 30)
        self.assertEqual(loaded_settings.bom.part_column, "零件号")
        self.assertTrue(loaded_settings.solidworks.visible)


if __name__ == "__main__":
    unittest.main()
