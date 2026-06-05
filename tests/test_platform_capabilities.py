import unittest
from unittest.mock import patch

from utils.platform_capabilities import detect_platform_capabilities


class PlatformCapabilitiesTests(unittest.TestCase):
    def test_non_windows_disables_solidworks_local_processing(self):
        capabilities = detect_platform_capabilities(platform_name="darwin")

        self.assertFalse(capabilities.solidworks_local_processing_available)
        self.assertIn("Windows", capabilities.solidworks_local_processing_reason)

    def test_windows_without_pywin32_disables_solidworks_local_processing(self):
        with patch("importlib.util.find_spec", return_value=None):
            capabilities = detect_platform_capabilities(platform_name="win32")

        self.assertFalse(capabilities.solidworks_local_processing_available)
        self.assertIn("pywin32", capabilities.solidworks_local_processing_reason)

    def test_windows_with_pywin32_enables_solidworks_local_processing(self):
        with patch("importlib.util.find_spec", return_value=object()):
            capabilities = detect_platform_capabilities(platform_name="win32")

        self.assertTrue(capabilities.solidworks_local_processing_available)
        self.assertEqual(capabilities.solidworks_local_processing_reason, "")


if __name__ == "__main__":
    unittest.main()
