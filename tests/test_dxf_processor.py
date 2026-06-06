import tempfile
import unittest
from pathlib import Path

from core.dxf_processor import DXFProcessor


class RecordingDXFProcessor(DXFProcessor):
    def __init__(self):
        self.calls = []

    def merge_directory_to_dxf(self, input_dir: Path, output_file: Path):
        self.calls.append((input_dir.name, output_file.name))
        return True, f"merged {input_dir.name}"


class DXFProcessorMergeGroupingTests(unittest.TestCase):
    def test_merge_by_thickness_handles_material_directories_without_subfolder(self):
        processor = RecordingDXFProcessor()

        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            source_dir = base_dir / "classified"
            output_dir = base_dir / "merged"
            (source_dir / "铝板").mkdir(parents=True)
            (source_dir / "铝板" / "part-a.dxf").write_text("0\nEOF\n", encoding="utf-8")
            (source_dir / "不锈钢板" / "T=2.0").mkdir(parents=True)
            (source_dir / "不锈钢板" / "T=2.0" / "part-b.dxf").write_text("0\nEOF\n", encoding="utf-8")
            output_dir.mkdir()

            success_count, fail_count, _logs = processor.merge_by_thickness(source_dir, output_dir)

        self.assertEqual(success_count, 2)
        self.assertEqual(fail_count, 0)
        self.assertEqual(
            processor.calls,
            [
                ("T=2.0", "不锈钢板_T=2.0_merged.dxf"),
                ("铝板", "铝板_merged.dxf"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
