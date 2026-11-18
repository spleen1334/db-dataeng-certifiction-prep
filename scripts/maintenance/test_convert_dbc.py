"""Focused synthetic tests; never execute archived notebook code."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.maintenance import convert_dbc as converter


class ConversionTests(unittest.TestCase):
    def test_order_and_exact_fidelity(self):
        commands = [{"position": "10", "guid": "b", "command": "x = 2\n",
                     "results": {"type": "ansi", "data": "old"}, "error": "historic"},
                    {"position": "2", "guid": "a", "command": "x = 1", "results": None}]
        result = converter.convert({"language": "python", "commands": commands}, {})
        self.assertEqual(result["cells"][1]["source"], "x = 1")
        meta = result["cells"][2]["metadata"]["archived_databricks"]
        self.assertEqual(meta["original_array_index"], 0)
        self.assertEqual(meta["original_command"], commands[0]["command"])
        self.assertEqual(meta["original_results"], commands[0]["results"])
        self.assertEqual(meta["original_errors"], {"error": "historic"})
        self.assertIn("Historical", result["cells"][2]["outputs"][1]["data"]["text/plain"])

    def test_magics_and_sql(self):
        for language, source, kind in [
            ("python", "%md\n# Hello", "markdown"),
            ("python", "%sql\nselect 1", "markdown"),
            ("sql", "select 1", "markdown"),
            ("python", "%sh echo hi", "markdown"),
            ("python", "%python\nprint(1)", "code"),
        ]:
            cell = converter.command_cells({"command": source}, 0, language)[0]
            self.assertEqual(cell["cell_type"], kind)
            self.assertEqual(cell["metadata"]["archived_databricks"]["original_command"], source)

    def test_error_scaffold_is_not_a_historical_failure(self):
        command = {"command": "x = 1", "error": None, "errorSummary": None,
                   "baseErrorDetails": {"scaffold": True}}
        cell = converter.command_cells(command, 0, "python")[0]
        self.assertEqual(cell["outputs"], [])
        self.assertEqual(cell["metadata"]["archived_databricks"]["original_errors"],
                         {"error": None, "errorSummary": None,
                          "baseErrorDetails": {"scaffold": True}})
        command["errorSummary"] = "Historical failure"
        cell = converter.command_cells(command, 0, "python")[0]
        self.assertEqual(len(cell["outputs"]), 1)
        self.assertIn("Historical archived error", cell["outputs"][0]["data"]["text/plain"])
        self.assertIn("Historical failure", cell["outputs"][0]["data"]["text/plain"])

    def test_nested_empty_and_unknown(self):
        payload = {"type": "listResults", "data": [
            {"type": "table", "schema": {"fields": [{"name": "a"}]}, "data": [[1]]},
            {"type": "table", "schema": ["a"], "data": []},
            {"type": "listResults", "data": []},
            {"type": "mystery", "data": {"kept": True}},
            {"type": "mimeBundle", "data": {"text/html": "<b>Hi</b>",
                                           "application/unusual": {"x": 1}}}]}
        outputs = converter.render_result(payload)
        self.assertEqual(len(outputs), 6)
        self.assertIn("empty", outputs[1]["data"]["text/plain"])
        self.assertIn("empty", outputs[2]["data"]["text/plain"])
        self.assertIn("kept", outputs[3]["data"]["text/plain"])
        self.assertEqual(outputs[4]["data"]["text/html"], "<b>Hi</b>")
        self.assertIn("application/unusual", outputs[5]["data"]["text/plain"])
        cell = converter.command_cells({"command": "select 1", "results": payload}, 0, "sql")
        self.assertEqual(cell[0]["metadata"]["archived_databricks"]["original_results"], payload)
        self.assertEqual(cell[1]["outputs"], outputs)

    def test_deterministic(self):
        doc = {"language": "python", "commands": [{"command": "print(1)", "position": 0}]}
        self.assertEqual(converter.pretty(converter.convert(doc, {})),
                         converter.pretty(converter.convert(doc, {})))

    def test_populated_table_sample_detection(self):
        empty = {"type": "table", "schema": [{"name": "column"}], "data": []}
        populated = {"type": "table", "schema": [{"name": "column", "type": "integer",
                                                 "metadata": {}}], "data": [[0]]}
        for result in (None, empty, {"type": "listResults", "data": [empty]},
                       {"type": "ansi", "data": "not a table"}):
            self.assertFalse(converter.has_populated_table(result))
        self.assertTrue(converter.has_populated_table(populated))
        self.assertTrue(converter.has_populated_table(
            {"type": "listResults", "data": [
                empty, {"type": "listResults", "data": [populated]}]}))
        rendered = converter.render_result(populated)[0]["data"]["text/plain"]
        self.assertEqual(rendered, "Archived table:\ncolumn\n0")

    def test_overwrite_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.ipynb"
            path.write_text(json.dumps({"metadata": {}, "cells": []}))
            with self.assertRaises(FileExistsError):
                converter.guarded(path, False)
            converter.guarded(path, True)
            path.write_text(json.dumps({"metadata": {"learning_enriched": True}}))
            with self.assertRaises(ValueError):
                converter.guarded(path, True)


if __name__ == "__main__":
    unittest.main()
