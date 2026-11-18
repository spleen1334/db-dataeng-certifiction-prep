"""Bounded synthetic tests; no supplied data mutation."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.maintenance import catalog_data


class CatalogTests(unittest.TestCase):
    def test_malformed_jsonl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.json"
            path.write_text('{"a": 1}\n\n{"a": invalid}\n{"a": null}\n')
            result = catalog_data.inspect_file(path, "sample.json")
            self.assertEqual(result["records"], 2)
            self.assertEqual(result["nonblank_lines"], 3)
            self.assertEqual(result["malformed_line_numbers"], [3])
            self.assertEqual(result["schema_hints"], {"a": ["int", "null"]})

    def test_headerless_csv_and_quoted_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "payments.csv"
            path.write_text('1,"Bank, Transfer"\n2,PayPal\n')
            result = catalog_data.inspect_file(path, "gizmobox/payments/payments.csv")
            self.assertFalse(result["header"])
            self.assertEqual(result["records"], 2)
            self.assertEqual(result["columns"], ["_c0", "_c1"])
            self.assertEqual(result["schema_hints"]["row_widths"], [2])

    def test_deterministic_catalog_and_archive_source_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data/gizmobox/payments").mkdir(parents=True)
            (root / "materials/archives").mkdir(parents=True)
            path = root / "data/gizmobox/payments/p.csv"
            path.write_bytes(b"1,2\n")
            (root / "data/README.md").write_text("ignored")
            with zipfile.ZipFile(root / "materials/archives/dea-course-v5.dbc", "w") as archive:
                archive.writestr("lesson.python", json.dumps({"commands": [
                    {"command": "gizmobox payments", "results": "secret-marker"}]}))
            first = catalog_data.generated(root)
            (root / "data/catalog.json").write_text(first["catalog.json"])
            self.assertEqual(first, catalog_data.generated(root))
            self.assertNotIn("secret-marker", first["catalog.json"])
            catalog = json.loads(first["catalog.json"])
            self.assertEqual(len(catalog["files"]), 1)
            self.assertEqual(catalog["files"][0]["lessons"], ["lesson.python"])
            self.assertEqual(path.read_bytes(), b"1,2\n")


if __name__ == "__main__":
    unittest.main()
