import importlib.util
import sys
import tempfile
import types
import unittest
from pathlib import Path

from config.settings import OutputConfig, SolidWorksConfig


def load_module_from_path(module_name, path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoreSettingsInjectionTests(unittest.TestCase):
    def test_bom_classifier_uses_configured_output_folder_names(self):
        module = load_module_from_path("bom_classifier_under_test", "core/bom_classifier.py")
        classifier = module.BOMClassifier(
            output_config=OutputConfig(
                result_dir="out",
                classified_dir="classified",
                processed_dxf_dir="processed",
                merged_dir="merged",
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            self.assertTrue(classifier.set_project_dir(temp_dir))
            base = Path(temp_dir)

        self.assertEqual(classifier.result_dir, base / "out")
        self.assertEqual(classifier.classified_dir, base / "out" / "classified")
        self.assertEqual(classifier.processed_dxf_dir, base / "out" / "processed")
        self.assertEqual(classifier.merged_dir, base / "out" / "merged")

    def test_sw_converter_uses_configured_template_dir_and_visibility(self):
        win32com_module = types.ModuleType("win32com")
        win32_client_module = types.ModuleType("win32com.client")
        win32_client_module.VARIANT = lambda *args: args
        pythoncom_module = types.ModuleType("pythoncom")
        pythoncom_module.VT_BYREF = 0x4000
        pythoncom_module.VT_I4 = 3
        utils_module = types.ModuleType("utils")
        utils_module.logger = types.SimpleNamespace(
            info=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
        )
        original_modules = {
            name: sys.modules.get(name)
            for name in ("win32com", "win32com.client", "pythoncom", "utils")
        }
        sys.modules["win32com"] = win32com_module
        sys.modules["win32com.client"] = win32_client_module
        sys.modules["pythoncom"] = pythoncom_module
        sys.modules["utils"] = utils_module

        try:
            module = load_module_from_path("sw_converter_under_test", "core/sw_converter.py")
            with tempfile.TemporaryDirectory() as temp_dir:
                converter = module.SWConverter(
                    solidworks_config=SolidWorksConfig(
                        template_dir=temp_dir,
                        visible=True,
                    )
                )

                self.assertEqual(converter.template_dir, Path(temp_dir))
                self.assertTrue(converter.visible)
        finally:
            for name, original in original_modules.items():
                if original is None:
                    sys.modules.pop(name, None)
                else:
                    sys.modules[name] = original


if __name__ == "__main__":
    unittest.main()
