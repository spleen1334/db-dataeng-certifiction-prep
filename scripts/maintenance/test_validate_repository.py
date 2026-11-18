import copy
from pathlib import Path
import tempfile
import unittest

if __package__:
    from . import convert_dbc
    from . import validate_repository as validator
else:
    import convert_dbc
    import validate_repository as validator


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.nb = convert_dbc.convert({"commands": [{"command": "x = 1", "position": 1}]}, {})

    def test_valid_notebook(self):
        self.assertEqual(validator.notebook_errors(self.nb), [])

    def test_historical_error_excludes_detail_scaffolding(self):
        self.assertFalse(validator.historical_error({"baseErrorDetails": {"present": True}}))
        self.assertFalse(validator.historical_error({"error": "", "errorSummary": ""}))
        self.assertTrue(validator.historical_error({"errorSummary": "historical failure"}))
        self.assertTrue(validator.historical_error({"error": "historical failure"}))

    def test_invalid_shapes(self):
        for mutate in (
            lambda n: n.update(nbformat=3),
            lambda n: n["cells"][0].update(source=[12]),
            lambda n: n["cells"][1].update(id=n["cells"][0]["id"]),
            lambda n: n["cells"][1].pop("id"),
            lambda n: n["cells"][1].update(outputs=[{"output_type": "display_data",
                                                     "metadata": {}, "data": {"text/plain": 2}}]),
            lambda n: n["cells"][1].update(outputs=[{"output_type": "error", "ename": "X",
                                                     "evalue": "", "traceback": [3]}]),
        ):
            nb = copy.deepcopy(self.nb)
            mutate(nb)
            self.assertTrue(validator.notebook_errors(nb))

    def test_enrichment_and_original_tamper(self):
        nb = copy.deepcopy(self.nb)
        nb["cells"].insert(0, {"metadata": {"learning_enriched": True}, "source": "guide"})
        self.assertTrue(validator.preserved_cells(nb, self.nb))
        nb["cells"][-1]["source"] = "changed"
        self.assertFalse(validator.preserved_cells(nb, self.nb))

    def test_order_is_preserved(self):
        nb = copy.deepcopy(self.nb)
        nb["cells"].reverse()
        self.assertFalse(validator.preserved_cells(nb, self.nb))

    def test_enrichment_required_and_counts_checked(self):
        report = {"enriched_cell_count": 0, "operation_annotations": [], "snapshot_paths": []}
        self.assertTrue(validator.enrichment_errors(self.nb, report))
        nb = copy.deepcopy(self.nb)
        nb["metadata"]["learning_enriched"] = True
        nb["cells"].append({"metadata": {"learning_enriched": True}, "source": "guide"})
        report["enriched_cell_count"] = 1
        self.assertEqual(validator.enrichment_errors(nb, report), [])
        report["operation_annotations"] = [{"original_cell_index": 1, "operations": ["read"]}]
        self.assertTrue(validator.enrichment_errors(nb, report))

    def test_snapshot_complete_bytes_and_recorded_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            raw = b"a,b\n1,2\n"
            (root / "data/a.csv").write_bytes(raw)
            source = ("Path: `data/a.csv`\n\nSHA-256: `" + convert_dbc.digest(raw)
                      + "`\n\nComplete supplied text (not generated output):\n\n```csv\n"
                      + raw.decode() + "\n```")
            nb = {"cells": [{"metadata": {"learning_enriched": True}, "source": source}]}
            self.assertTrue(validator.snapshots_valid(nb, root, ["data/a.csv"]))
            self.assertFalse(validator.snapshots_valid(nb, root, []))
            nb["cells"][0]["source"] = source.replace("1,2", "1,3")
            self.assertFalse(validator.snapshots_valid(nb, root, ["data/a.csv"]))

    def test_local_links_decoding_fragments_and_remote(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a b.md").write_text("ok")
            page = root / "README.md"
            page.write_text("[ok](a%20b.md#heading) [web](https://example.invalid/x) "
                            "[fragment](#x)\n```\n[ignored](missing)\n```")
            self.assertEqual(validator.local_links(page, root), 0)
            page.write_text("![bad](missing.png)")
            self.assertEqual(validator.local_links(page, root), 1)


if __name__ == "__main__":
    unittest.main()
