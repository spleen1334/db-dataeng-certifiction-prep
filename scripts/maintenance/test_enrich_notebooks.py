import copy
import hashlib
import tempfile
import unittest
from pathlib import Path

from enrich_notebooks import enrich, safe_targets


class EnrichmentTests(unittest.TestCase):
    def notebook(self, command):
        return {"metadata": {"archived_databricks": {"member": "course/Join.sql"}},
                "cells": [{"cell_type": "code", "source": command, "outputs": [
                    {"output_type": "display_data", "data": {"text/html": "<b>saved</b>"}}],
                    "metadata": {"archived_databricks": {"original_command": command,
                                                       "position": 2, "original_results": {"x": 1}}}}]}

    def test_idempotency_and_preservation(self):
        before = self.notebook("SELECT * FROM a JOIN b ON a.id=b.id")
        untouched = copy.deepcopy(before)
        after, report = enrich(before, Path("Join.ipynb"))
        again, report2 = enrich(after, Path("Join.ipynb"))
        self.assertEqual(after, again)
        self.assertEqual(report, report2)
        self.assertEqual(before, untouched)
        self.assertEqual([c for c in after["cells"] if not c["metadata"].get("learning_enriched")],
                         before["cells"])
        self.assertIn("join", report["operation_annotations"][0]["operations"])
        self.assertIn("Join", report["reviewed_lesson_title"])

    def test_linked_attributed_inputs_not_embedded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "data/gizmobox/orders"
            folder.mkdir(parents=True)
            raw = b'{"id":1}\nBROKEN\n{"id":2}\n'
            (folder / "part.json").write_bytes(raw)
            unrelated = root / "data/gizmobox/payments"
            unrelated.mkdir()
            (unrelated / "other.csv").write_text("unrelated")
            entries = [
                dict(path="gizmobox/orders/part.json", family="gizmobox", dataset="orders",
                     lessons=["course/Join.sql"], malformed_line_numbers=[2]),
                dict(path="gizmobox/payments/other.csv", family="gizmobox", dataset="payments",
                     lessons=["course/Other.sql"])]
            nb, report = enrich(self.notebook("read_files('/gizmobox/orders/')"),
                                Path("Join.ipynb"), root, {"files": entries})
            prose = "\n".join(c["source"] for c in nb["cells"] if c["metadata"].get("learning_enriched"))
            self.assertNotIn(raw.decode(), prose)
            self.assertIn("Original inputs: gizmobox/orders", prose)
            self.assertIn("1 files", prose)
            self.assertNotIn("unrelated", prose)
            self.assertEqual(report["input_paths"], ["data/gizmobox/orders/part.json"])
            self.assertIn("malformed", prose)
            self.assertFalse(report["external_input_claim"])

    def test_specific_notes_and_no_secret_copy(self):
        nb, report = enrich(self.notebook(
            "password='do-not-copy'\nMERGE INTO t USING s ON t.id=s.id\n"
            "readStream.option('checkpointLocation','x')\nVACUUM t"),
            Path("lesson.ipynb"))
        notes = "\n".join(c["source"] for c in nb["cells"] if c["metadata"].get("learning_enriched"))
        self.assertIn("MERGE", notes)
        self.assertLessEqual(len(report["operation_annotations"]), 3)
        self.assertNotIn("do-not-copy", notes)
        self.assertTrue(report["operation_annotations"])

    def test_companies_limitation_and_teaching_examples(self):
        source = "SELECT * FROM bronze_companies JOIN silver_companies ON a.id=b.id"
        course, _ = enrich(self.notebook(source), Path("gold_companies.ipynb"))
        standalone, _ = enrich(self.notebook(source), Path("companies_report.ipynb"))
        def notes(nb):
            return "\n".join(c["source"] for c in nb["cells"]
                             if c["metadata"].get("learning_enriched"))
        self.assertNotIn("remote companies table is absent", notes(course))
        self.assertIn("remote companies table is absent", notes(standalone))
        self.assertNotIn("Unexecuted teaching example", notes(course))
        self.assertIn("cardinality", notes(course))

    def test_relation_extraction_ignores_markdown_comments_and_outputs(self):
        nb = self.notebook("%md\nJoin customer_address table which comes from customer")
        nb["cells"].extend([
            {"cell_type": "markdown", "source": "table which from customer", "metadata": {}},
            {"cell_type": "code", "source": "# from invented\nspark.table('catalog.real')\ndf.write.saveAsTable('catalog.target')",
             "metadata": {}},
            {"cell_type": "code", "source": "SELECT * FROM output_fake",
             "metadata": {"archived_output_only": True}},
            {"cell_type": "code", "source": "%sql\n-- FROM comment_fake\nSELECT * FROM actual",
             "metadata": {}},
        ])
        self.assertEqual(safe_targets(nb["cells"]), ["actual", "catalog.real", "catalog.target"])

    def test_curated_companies_inputs_are_not_claimed_source_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "data/top_tech_companies"
            folder.mkdir(parents=True)
            entries = []
            for number in (1, 2):
                name = f"top_tech_companies_{number}.csv"
                (folder / name).write_text("company_name,founded_date,country\nExample,2000,US\n")
                entries.append({"path": "top_tech_companies/" + name, "lessons": []})
            for name in ("01. bronze_companies", "02. silver_companies",
                         "03. gold_companies", "companies_report"):
                enriched, report = enrich(self.notebook("SELECT * FROM remote_companies"),
                                          Path(name + ".ipynb"), root, {"files": entries})
                self.assertEqual(len(report["related_input_attributions"]), 2)
                self.assertFalse(report["related_input_attributions"][0]["automatic_source_match"])
                self.assertFalse(report["related_input_attributions"][0]["original_remote_contents_verified"])
                prose = "\n".join(cell["source"] for cell in enriched["cells"]
                                  if cell["metadata"].get("learning_enriched"))
                self.assertIn("not verified to be identical", prose)
                self.assertIn("schema-compatible", prose)


if __name__ == "__main__":
    unittest.main()
