"""Focused external-payload and compact-enrichment regression checks."""
import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import convert_dbc as converter
import enrich_notebooks as enricher
import validate_repository as validator
import clean_notebooks as cleaner


class CompactPipelineTests(unittest.TestCase):
    def setUp(self):
        self.doc = {"language": "python", "commands": [
            {"command": "print('unchanged')", "guid": "a", "position": 1,
             "results": {"type": "text", "data": "saved"}, "baseErrorDetails": {"secret": "detail"}},
            {"command": "%sql\nSELECT * FROM a JOIN b ON a.id=b.id", "position": 2}]}
        self.raw = json.dumps(self.doc).encode()
        self.provenance = {"member": "course/section/lesson.python",
                           "member_sha256": converter.digest(self.raw)}

    def test_external_exact_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.ipynb"
            payload = converter.pretty(converter.payload_document(self.raw, self.provenance)).encode()
            (path.parent / "payload.json").write_bytes(payload)
            nb = converter.convert(self.doc, self.provenance, "payload.json")
            nb["metadata"]["archived_databricks"]["payload_sha256"] = converter.digest(payload)
            self.assertEqual([], validator.compact_payload_errors(nb, path, self.raw, self.provenance))
            metadata = nb["cells"][1]["metadata"]["archived_databricks"]
            self.assertNotIn("original_results", metadata)
            self.assertNotIn("original_command", metadata)
            self.assertEqual("print('unchanged')", nb["cells"][1]["source"])
            nb["cells"][1]["source"] += "# learner edit"
            self.assertTrue(validator.compact_payload_errors(nb, path, self.raw, self.provenance))

    def test_no_snapshots_idempotent_and_selective(self):
        nb = converter.convert(self.doc, self.provenance, "payload.json")
        enriched, report = enricher.enrich(nb, Path("lesson.ipynb"))
        self.assertEqual([], report["input_paths"])
        self.assertNotIn("snapshot_paths", report)
        self.assertLessEqual(len(report["operation_annotations"]), 3)
        self.assertEqual(enriched, enricher.enrich(enriched, Path("lesson.ipynb"))[0])

    def test_enriched_overwrite_still_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lesson.ipynb"
            path.write_text(json.dumps({"metadata": {"learning_enriched": True}}))
            with self.assertRaises(ValueError):
                converter.guarded(path, True)

    def test_standalone_preserves_source(self):
        raw = json.dumps({"cells": [{"cell_type": "code", "metadata": {},
            "source": ["print(1)\n"], "execution_count": 5,
            "outputs": [{"output_type": "stream", "name": "stdout", "text": "1\n"}]}],
            "metadata": {}, "nbformat": 4, "nbformat_minor": 4}).encode()
        nb = converter.compact_standalone(raw, self.provenance, "payload.json")
        self.assertEqual(["print(1)\n"], nb["cells"][1]["source"])
        self.assertEqual(None, nb["cells"][1]["execution_count"])

    def test_install_guard_accepts_baselines_and_refuses_learner_edits(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "lesson.ipynb"
            old = converter.convert(self.doc, self.provenance)
            compact = converter.convert(self.doc, self.provenance, "payload.json")
            for baseline in (old, compact):
                enriched, _ = enricher.enrich(baseline, target)
                target.write_text(json.dumps(enriched))
                cleaner.preflight_existing(target, [old, compact])
                enriched["cells"][-1]["source"] = "learner changes"
                target.write_text(json.dumps(enriched))
                with self.assertRaises(ValueError):
                    cleaner.preflight_existing(target, [old, compact])

    def test_local_notebook_links_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            self.assertEqual(0, validator.local_link_errors("[input](data/)", root / "n.ipynb", root))
            self.assertEqual(1, validator.local_link_errors("[input](absent.json)", root / "n.ipynb", root))

    def test_standalone_normalizes_text_mime_lists(self):
        raw = json.dumps({"cells": [{"cell_type": "code", "source": "x",
            "metadata": {}, "outputs": [{"output_type": "display_data",
            "data": {"text/plain": ["a", "b"], "text/html": ["<table>", "</table>"]}}]}],
            "metadata": {}}).encode()
        with patch.object(converter, "compact_result", return_value=[]) as render:
            converter.compact_standalone(raw, self.provenance, "payload.json")
        self.assertEqual({"text/plain": "ab", "text/html": "<table></table>"},
                         render.call_args.args[0]["data"])

    def test_install_preflights_every_notebook_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for folder in ("materials/archives", "data", "artifacts/metadata", "materials/originals"):
                (root / folder).mkdir(parents=True)
            for name in ("dea-course-v5.dbc", "dea05-databricks-jobs.dbc"):
                (root / "materials/archives" / name).write_bytes(b"fixture")
            (root / "data/catalog.json").write_text('{"files":[]}')
            assets = []
            original = {"nbformat": 4, "nbformat_minor": 4, "metadata": {}, "cells": []}
            for index in range(2):
                asset = {"new": f"materials/originals/{index}.ipynb",
                         "study_copy": f"notebooks/standalone/{index}.ipynb"}
                (root / asset["new"]).write_text(json.dumps(original))
                assets.append(asset)
            (root / "artifacts/metadata/source-map.json").write_text(json.dumps({"assets": assets}))
            records = [(f"course/section/{i}.python", self.raw, self.doc) for i in range(69)]
            visited = []
            def preflight(target, baselines):
                visited.append(target)
                if len(visited) == 71:
                    raise ValueError("fixture learner edit")
            with patch.object(cleaner, "ROOT", root), \
                    patch.object(converter, "members", side_effect=lambda p: records if p.name == "dea-course-v5.dbc" else []), \
                    patch.object(cleaner, "preflight_existing", side_effect=preflight):
                with self.assertRaisesRegex(ValueError, "fixture learner edit"):
                    cleaner.generate(root, install=True)
            self.assertEqual(71, len(visited))
            self.assertFalse((root / "artifacts/notebook-payloads").exists())
            self.assertFalse((root / "artifacts/metadata/enrichment-report.json").exists())
            self.assertFalse((root / "notebooks").exists())


if __name__ == "__main__":
    unittest.main()
