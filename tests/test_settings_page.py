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

        page.part_column_edit.setText("零件号")
        page.material_split_markers_edit.setText("板;钢")
        page.inventory_export_prefix_edit.setText("现场库存")
        page.solidworks_visible_check.setChecked(True)
        page.admin_password_edit.setText("new-offline-pass")

        saved_settings = page.save_current_settings(show_message=False)
        loaded_settings = load_settings(store=store)

        self.assertEqual(saved_settings.app.theme, "dark_teal.xml")
        self.assertEqual(loaded_settings.remote_api.base_url, "")
        self.assertEqual(loaded_settings.remote_api.timeout_seconds, 15)
        self.assertEqual(loaded_settings.bom.part_column, "零件号")
        self.assertEqual(loaded_settings.bom.material_split_markers, "板;钢")
        self.assertEqual(loaded_settings.inventory.export_filename_prefix, "现场库存")
        self.assertTrue(loaded_settings.solidworks.visible)
        self.assertEqual(loaded_settings.auth.fallback_admin_username, "admin")
        self.assertEqual(loaded_settings.auth.fallback_admin_password, "new-offline-pass")

    def test_settings_page_does_not_edit_theme_or_remote_api(self):
        page = SettingsPage(AppSettings(), store=InMemorySettingsStore())

        self.assertFalse(hasattr(page, "theme_edit"))
        self.assertFalse(hasattr(page, "api_base_url_edit"))
        self.assertFalse(hasattr(page, "api_timeout_spin"))
        self.assertEqual(page.admin_username_label.text(), "admin")

    def test_blank_offline_password_keeps_existing_password(self):
        store = InMemorySettingsStore()
        settings = AppSettings()
        page = SettingsPage(settings, store=store)

        page.admin_password_edit.setText("")

        saved_settings = page.save_current_settings(show_message=False)
        loaded_settings = load_settings(store=store)

        self.assertEqual(saved_settings.auth.fallback_admin_password, "#456@admin")
        self.assertEqual(loaded_settings.auth.fallback_admin_password, "#456@admin")


if __name__ == "__main__":
    unittest.main()
