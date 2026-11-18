"""Compact, static previews of archived Databricks results; never executes them."""

import base64
import binascii
import html
from html.parser import HTMLParser
import re

MAX_ROWS = 10
MAX_CELL = 200
MAX_OUTPUTS = 20
MAX_IMAGE_BYTES = 300_000
REFERENCE = "Full archived values are in the linked payload reference in the notebook header."
_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
_BINARY = re.compile(r"^[A-Za-z0-9+/=\s]{160,}$")
_MISSING = object()


def _output(text, markup=None):
    data = {"text/plain": text}
    if markup is not None:
        data["text/html"] = markup
    return {"output_type": "display_data", "metadata": {}, "data": data}


def _value(value):
    if value is _MISSING:
        return "[missing]"
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        # Do not stringify huge binary/nested structures into the notebook.
        return "[nested value omitted]"
    if isinstance(value, (bytes, bytearray)):
        return "[binary value omitted]"
    text = _ANSI.sub("", str(value))
    if _BINARY.fullmatch(text):
        return "[binary or encoded value omitted]"
    if len(text) > MAX_CELL:
        return text[:MAX_CELL] + "… [truncated]"
    return text


def _columns(schema, rows):
    if isinstance(schema, dict):
        schema = schema.get("fields", schema)
    if isinstance(schema, list) and schema:
        return [str(field.get("name", i)) if isinstance(field, dict) else str(field)
                for i, field in enumerate(schema)]
    if isinstance(schema, dict) and schema:
        return list(map(str, schema))
    if rows and isinstance(rows[0], dict):
        return list(map(str, rows[0]))
    return []


def _table(result):
    rows = result.get("data")
    if not isinstance(rows, list):
        return _output("Archived table: saved rows unavailable. " + REFERENCE)
    columns = _columns(result.get("schema"), rows)
    # Preserve fields found in rows even when the archived schema is incomplete.
    for row in rows:
        if isinstance(row, dict):
            for key in row:
                if str(key) not in columns:
                    columns.append(str(key))
        elif isinstance(row, (list, tuple)):
            columns.extend(f"Column {i + 1}" for i in range(len(columns), len(row)))
        elif not columns:
            columns.append("Value")
    count = min(len(rows), MAX_ROWS)
    caption = f"Archived result · {count} of {len(rows)} saved rows shown."
    caption += " " + REFERENCE
    headers = [_value(c) for c in columns]
    rendered = []
    for row in rows[:MAX_ROWS]:
        if isinstance(row, dict):
            values = [row.get(c, _MISSING) for c in columns]
        elif isinstance(row, (list, tuple)):
            values = [row[i] if i < len(row) else _MISSING for i in range(len(columns))]
        else:
            values = [row] + [_MISSING] * max(0, len(columns) - 1)
        rendered.append([_value(v) for v in values])
    lines = [caption]
    if headers:
        lines.append(" | ".join(headers))
    lines.extend(" | ".join(v.replace("\n", " ") for v in row) for row in rendered)
    esc = html.escape
    style = "padding:4px 10px;text-align:left;vertical-align:top;border-bottom:1px solid currentColor;"
    markup = ('<div style="overflow-x:auto;max-width:100%">'
              f'<p>{esc(caption)}</p><table style="border-collapse:collapse;font-size:0.9em">'
              "<thead><tr>" + "".join(f'<th scope="col" style="{style}">{esc(h)}</th>' for h in headers)
              + "</tr></thead><tbody>")
    for row in rendered:
        markup += "<tr>" + "".join(
            f'<td style="{style};white-space:pre-wrap;overflow-wrap:anywhere">{esc(v)}</td>'
            for v in row) + "</tr>"
    markup += "</tbody></table></div>"
    return _output("\n".join(lines), markup)


def _safe_image(mime, value):
    signatures = {"image/png": b"\x89PNG\r\n\x1a\n",
                  "image/jpeg": b"\xff\xd8\xff", "image/gif": b"GIF8"}
    if mime not in signatures or not isinstance(value, str):
        return False
    if len(value) > (MAX_IMAGE_BYTES * 4 // 3 + 8):
        return False
    try:
        raw = base64.b64decode(value, validate=True)
        return len(raw) <= MAX_IMAGE_BYTES and raw.startswith(signatures[mime])
    except (binascii.Error, ValueError):
        return False


def _text(value):
    """Normalize notebook MIME strings, which may be split into lines."""
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(part, str) for part in value):
        return "".join(value)
    return None


class _ArchivedTable(HTMLParser):
    """Extract text cells from the first table, discarding all HTML attributes."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = 0
        self.depth = 0
        self.ignored = 0
        self.in_head = False
        self.row = None
        self.cell = None
        self.rows = []
        self.headers = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.ignored += 1
            return
        if self.ignored:
            return
        if tag == "table":
            self.depth += 1
            if self.depth == 1:
                self.tables += 1
        if self.tables != 1 or self.depth != 1:
            return
        if tag == "thead":
            self.in_head = True
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.ignored:
            self.ignored -= 1
            return
        if self.ignored:
            return
        if self.tables == 1 and self.depth == 1:
            if tag in ("td", "th") and self.cell is not None:
                self.row.append("".join(self.cell).strip())
                self.cell = None
            elif tag == "tr" and self.row is not None:
                if self.in_head and not self.headers:
                    self.headers = self.row
                elif not self.in_head:
                    self.rows.append(self.row)
                self.row = None
            elif tag == "thead":
                self.in_head = False
        if tag == "table" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if not self.ignored and self.cell is not None and self.depth == 1:
            self.cell.append(data)


def _html_table(value):
    text = _text(value)
    if not text:
        return None
    parser = _ArchivedTable()
    try:
        parser.feed(text)
        parser.close()
    except (ValueError, AssertionError):
        return None
    if not parser.tables or not (parser.headers or parser.rows):
        return None
    output = _table({"schema": [{"name": name} for name in parser.headers],
                     "data": parser.rows})
    if parser.tables > 1:
        notice = " Additional archived tables omitted. " + REFERENCE
        output["data"]["text/plain"] += "\n" + notice.strip()
        output["data"]["text/html"] += "<p>" + html.escape(notice.strip()) + "</p>"
    return output


def render_result(result):
    """Return bounded nbformat display_data previews of saved results."""
    outputs = []
    omitted = 0
    empty = 0

    def visit(item):
        nonlocal omitted, empty
        if item is None:
            return
        if isinstance(item, dict) and item.get("type") == "listResults" and isinstance(item.get("data"), list):
            if not item["data"]:
                empty += 1
            for child in item["data"]:
                visit(child)
            return
        if len(outputs) >= MAX_OUTPUTS:
            omitted += 1
            return
        if not isinstance(item, dict):
            outputs.append(_output("Archived result: unsupported value omitted. " + REFERENCE))
            return
        kind, data = item.get("type"), item.get("data")
        if kind == "table":
            if data == [] and not _columns(item.get("schema"), []):
                empty += 1
            else:
                outputs.append(_table(item))
        elif kind in ("text", "ansi") and isinstance(data, str):
            outputs.append(_output("Archived output:\n" + _value(data) + "\n" + REFERENCE))
        elif kind == "mimeBundle" and isinstance(data, dict):
            table = _html_table(data.get("text/html"))
            image = next(((mime, value) for mime, value in data.items()
                          if _safe_image(mime, value)), None)
            plain = _text(data.get("text/plain"))
            if table:
                outputs.append(table)
            elif image:
                mime, value = image
                outputs.append({"output_type": "display_data", "metadata": {},
                                "data": {"text/plain": "Archived image. " + REFERENCE,
                                         mime: value}})
            elif plain:
                outputs.append(_output("Archived output:\n" + _value(plain) + "\n" + REFERENCE))
            else:
                outputs.append(_output("Archived rich output omitted. " + REFERENCE))
        elif kind in ("html", "htmlSandbox"):
            outputs.append(_html_table(data) or _output("Archived HTML output omitted. " + REFERENCE))
        else:
            outputs.append(_output("Archived output omitted. " + REFERENCE))

    visit(result)
    if empty:
        outputs.append(_output(f"Archived empty results: {empty}. " + REFERENCE))
    if omitted:
        outputs.append(_output(f"Additional archived results omitted: {omitted}. " + REFERENCE))
    return outputs
