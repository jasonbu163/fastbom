import unittest

from core.bom_classifier import BOMClassifier


class BOMClassifierMaterialParsingTests(unittest.TestCase):
    def test_material_split_markers_follow_configured_order(self):
        classifier = BOMClassifier()

        material, subfolder = classifier.parse_material("不锈钢板 T=2.0", "钢;板")

        self.assertEqual(material, "不锈钢")
        self.assertEqual(subfolder, "板 T=2.0")

    def test_material_split_marker_keeps_tail_text_and_normalizes_spaces(self):
        classifier = BOMClassifier()

        material, subfolder = classifier.parse_material(" 铝板   T =   2.0 ", ["板"])

        self.assertEqual(material, "铝板")
        self.assertEqual(subfolder, "T=2.0")

    def test_material_without_matching_marker_uses_single_directory(self):
        classifier = BOMClassifier()

        material, subfolder = classifier.parse_material(" 304不锈钢   T = 3 ", ["板"])

        self.assertEqual(material, "304不锈钢 T=3")
        self.assertIsNone(subfolder)


if __name__ == "__main__":
    unittest.main()
