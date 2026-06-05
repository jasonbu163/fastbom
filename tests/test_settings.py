import unittest

from config.settings import InMemorySettingsStore, AppSettings, can_use_remote_forms, load_settings, save_settings


class SettingsTests(unittest.TestCase):
    def test_defaults_preserve_current_behavior(self):
        settings = load_settings(store=InMemorySettingsStore())

        self.assertEqual(settings.app.theme, "dark_teal.xml")
        self.assertEqual(settings.bom.part_column, "图号")
        self.assertEqual(settings.bom.material_column, "材料")
        self.assertEqual(settings.bom.quantity_column, "总数量")
        self.assertEqual(settings.output.result_dir, "result")
        self.assertEqual(settings.output.classified_dir, "1_分类结果")
        self.assertEqual(settings.output.processed_dxf_dir, "2_DXF处理结果")
        self.assertEqual(settings.output.merged_dir, "3_合并文件")
        self.assertEqual(settings.solidworks.template_dir, "template")
        self.assertFalse(settings.solidworks.visible)
        self.assertEqual(settings.dxf.text_layer, "0")
        self.assertEqual(settings.dxf.text_color, 2)
        self.assertEqual(settings.dxf.text_height, 50.0)
        self.assertEqual(settings.dxf.spacing, 100.0)
        self.assertEqual(settings.remote_api.base_url, "")
        self.assertEqual(settings.remote_api.timeout_seconds, 15)
        self.assertEqual(settings.auth.fallback_admin_username, "admin")
        self.assertEqual(settings.auth.fallback_admin_password, "")

    def test_qsettings_store_overrides_built_in_defaults(self):
        store = InMemorySettingsStore(
            {
                "app.theme": "stored_theme.xml",
                "bom.part_column": "零件号",
                "remote_api.base_url": "https://stored.example.test",
                "remote_api.timeout_seconds": "30",
                "solidworks.visible": "true",
            }
        )

        settings = load_settings(store=store)

        self.assertEqual(settings.app.theme, "stored_theme.xml")
        self.assertEqual(settings.bom.part_column, "零件号")
        self.assertEqual(settings.remote_api.base_url, "https://stored.example.test")
        self.assertEqual(settings.remote_api.timeout_seconds, 30)
        self.assertTrue(settings.solidworks.visible)

    def test_save_settings_persists_values_to_store(self):
        store = InMemorySettingsStore()
        settings = AppSettings()
        settings = type(settings)(
            app=type(settings.app)(theme="stored_theme.xml"),
            bom=settings.bom,
            output=settings.output,
            solidworks=settings.solidworks,
            dxf=settings.dxf,
            remote_api=type(settings.remote_api)(
                base_url="https://api.example.test",
                timeout_seconds=45,
            ),
            auth=settings.auth,
        )

        save_settings(settings, store)
        loaded_settings = load_settings(store=store)

        self.assertEqual(loaded_settings.app.theme, "stored_theme.xml")
        self.assertEqual(loaded_settings.remote_api.base_url, "https://api.example.test")
        self.assertEqual(loaded_settings.remote_api.timeout_seconds, 45)

    def test_fallback_admin_session_cannot_use_remote_forms(self):
        self.assertFalse(can_use_remote_forms("fallback_admin"))
        self.assertTrue(can_use_remote_forms("backend_user"))


if __name__ == "__main__":
    unittest.main()
