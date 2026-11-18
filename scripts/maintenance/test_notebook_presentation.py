import base64
import unittest

from notebook_presentation import MAX_CELL, MAX_ROWS, render_result


class PresentationTests(unittest.TestCase):
    def test_table_escapes_and_bounds(self):
        rows = [[f"<script>{i}</script>", ("x!" * MAX_CELL), None]
                for i in range(MAX_ROWS + 3)]
        output = render_result({"type": "table", "schema": [
            {"name": '<img src=x onerror="x">'}, {"name": "long"}, {"name": "null"}],
            "data": rows})[0]["data"]
        markup = output["text/html"]
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;0&lt;/script&gt;", markup)
        self.assertIn("&lt;img", markup)
        self.assertIn("10 of 13 saved rows shown", markup)
        self.assertIn("[truncated]", markup)
        self.assertNotIn("x!" * MAX_CELL, markup)
        self.assertIn("null", output["text/plain"])
        self.assertEqual(markup.count("<tr>"), MAX_ROWS + 1)

    def test_empty_nested_and_missing(self):
        result = {"type": "listResults", "data": [
            {"type": "listResults", "data": []},
            {"type": "table", "data": []},
            {"type": "table", "schema": [{"name": "a"}, {"name": "b"}],
             "data": [{"a": None}]}]}
        outputs = render_result(result)
        self.assertEqual(len(outputs), 2)
        self.assertIn("null | [missing]", outputs[0]["data"]["text/plain"])
        self.assertIn("empty results: 2", outputs[1]["data"]["text/plain"])
        self.assertEqual(render_result(None), [])

    def test_columns_and_binary_nested_values(self):
        data = render_result({"type": "table", "schema": [{"name": "id"}],
                              "data": [{"id": 1, "payload": "A" * 500, "nested": [1, 2]}]})[0]["data"]
        self.assertIn("payload", data["text/html"])
        self.assertIn("[binary or encoded value omitted]", data["text/plain"])
        self.assertIn("[nested value omitted]", data["text/plain"])

    def test_untrusted_rich_payload_and_unknown(self):
        for item in [
            {"type": "htmlSandbox", "data": "<script>alert(1)</script>"},
            {"type": "mimeBundle", "data": {"text/html": "<script>alert(1)</script>"}},
            {"type": "mystery", "data": "secret payload"},
        ]:
            output = render_result(item)[0]["data"]
            self.assertNotIn("text/html", output)
            self.assertNotIn("secret payload", str(output))
            self.assertNotIn("<script>", str(output))

    def test_safe_image_and_ansi(self):
        png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode()
        result = render_result({"type": "mimeBundle", "data": {"image/png": png}})[0]["data"]
        self.assertEqual(result["image/png"], png)
        result = render_result({"type": "ansi", "data": "\x1b[31mred\x1b[0m"})[0]["data"]
        self.assertIn("red", result["text/plain"])
        self.assertNotIn("\x1b", result["text/plain"])

    def test_html_table_rebuilt_without_active_markup(self):
        markup = ('<table onclick="bad()"><thead><tr><th>Name &amp; value</th>'
                  '<th>Result</th></tr></thead><tbody>'
                  '<tr><th>row &lt;1&gt;</th><td>safe<script>bad()</script>'
                  '<style>bad</style><img src=x onerror="bad()"> &amp; sound</td></tr>'
                  '</tbody></table><table><tr><td>second</td></tr></table>')
        data = render_result({"type": "mimeBundle", "data": {
            "text/html": [markup[:80], markup[80:]], "text/plain": ["fallback"]}})[0]["data"]
        self.assertIn("Name &amp; value", data["text/html"])
        self.assertIn("row &lt;1&gt;", data["text/html"])
        self.assertIn("safe &amp; sound", data["text/html"])
        self.assertIn("Name & value", data["text/plain"])
        self.assertIn("1 of 1 saved rows", data["text/plain"])
        self.assertIn("Additional archived tables omitted", data["text/plain"])
        self.assertNotIn("onclick", data["text/html"])
        self.assertNotIn("onerror", data["text/html"])
        self.assertNotIn("<script", data["text/html"])
        self.assertNotIn("bad()", data["text/plain"])

    def test_mime_list_text_fallback(self):
        output = render_result({"type": "mimeBundle", "data": {
            "text/html": ["<div>not a table</div>"],
            "text/plain": ["first ", "line"]}})[0]["data"]
        self.assertIn("first line", output["text/plain"])
        self.assertNotIn("text/html", output)


if __name__ == "__main__":
    unittest.main()
