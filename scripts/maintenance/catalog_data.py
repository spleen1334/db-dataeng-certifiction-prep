#!/usr/bin/env python3
"""Deterministic, stdlib-only inventory; never modifies supplied inputs."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = {"README.md", "catalog.json", "catalog.md"}


def inspect_file(path, relative):
    raw = path.read_bytes()
    result = dict(path=relative, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                  format=path.suffix.lstrip("."), records=None, columns=[],
                  schema_hints={}, malformed_line_numbers=[], role="local_input")
    if path.suffix in {".csv", ".tsv"}:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig")),
                               delimiter="\t" if path.suffix == ".tsv" else ","))
        rows = [row for row in rows if row]
        header = "/payments/" not in "/" + relative
        result.update(header=header, records=max(0, len(rows) - int(header)),
                      columns=(rows[0] if header and rows else
                               [f"_c{i}" for i in range(len(rows[0]) if rows else 0)]))
        result["schema_hints"] = {"column_types": "text; no coercion",
                                  "row_widths": sorted({len(row) for row in rows})}
    elif path.suffix == ".json":
        text = raw.decode("utf-8-sig")
        try:
            value = json.loads(text)
            values = value if isinstance(value, list) else [value]
            result["format"] = "json"
        except json.JSONDecodeError:
            values = []
            result["format"] = "jsonl"
            result["nonblank_lines"] = sum(bool(line.strip()) for line in text.splitlines())
            for number, line in enumerate(text.splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    values.append(json.loads(line))
                except json.JSONDecodeError:
                    result["malformed_line_numbers"].append(number)
        hints = {}
        for value in values:
            if isinstance(value, dict):
                for key, item in value.items():
                    hints.setdefault(key, set()).add(
                        "null" if item is None else type(item).__name__)
        result.update(records=len(values), columns=sorted(hints),
                      schema_hints={key: sorted(types) for key, types in sorted(hints.items())})
    elif path.suffix == ".png":
        if raw[:8] == b"\x89PNG\r\n\x1a\n" and raw[12:16] == b"IHDR":
            width, height = struct.unpack(">II", raw[16:24])
            result["schema_hints"] = dict(width=width, height=height,
                                           bit_depth=raw[24], color_type=raw[25])
    elif path.suffix == ".sql":
        result["role"] = "local_external_database_setup"
        result["schema_hints"] = {
            "table": "Refunds", "columns": ["refund_id", "payment_id", "refund_timestamp",
                                           "refund_amount", "refund_reason"],
            "records": "INSERT tuples; not counted as data-file records",
            "known_issue": "Line 6 ends with NOT NULL. (period), preserved verbatim",
            "root_copy": "scripts/sql/refunds_azure_sql_ddl.sql"}
        result["columns"] = result["schema_hints"]["columns"]
    return result


def archive_lessons(archive):
    """Match only command source; never export command text, results or secrets."""
    lessons = []
    with zipfile.ZipFile(archive) as source:
        for name in sorted(source.namelist()):
            if not name.endswith((".python", ".sql")):
                continue
            notebook = json.loads(source.read(name))
            commands = "\n".join(c.get("command", "") for c in notebook.get("commands", []))
            lessons.append((name, commands.lower()))
    return lessons


def build(root):
    lessons = archive_lessons(root / "docs/originals/dea-course-v5.dbc")
    files = []
    for path in sorted((root / "data").rglob("*")):
        if not path.is_file() or path.name in EXCLUDED:
            continue
        relative = path.relative_to(root / "data").as_posix()
        entry = inspect_file(path, relative)
        parts = relative.split("/")
        family = parts[0]
        dataset = parts[1] if len(parts) > 2 else family
        # Family plus lane/entity references are evidence, not claimed exact file reads.
        matches = [name for name, command in lessons
                   if family in command and
                   (dataset in command or dataset.replace("_", "") in command)]
        entry.update(family=family, dataset=dataset, lessons=matches,
                     lesson_evidence="family and dataset tokens in archived command source")
        files.append(entry)
    hashes = {}
    for entry in files:
        hashes.setdefault(entry["sha256"], []).append(entry["path"])
    duplicates = []
    lanes = {"customers", "customers_stream", "customers_autoloader"}
    for digest, paths in sorted(hashes.items()):
        if len(paths) > 1:
            intentional = all(p.startswith("gizmobox/") and p.split("/")[1] in lanes
                              for p in paths)
            duplicates.append(dict(sha256=digest, paths=paths, intentional=intentional,
                                   reason="Separate batch, streaming and Auto Loader ingestion lanes"
                                   if intentional else "Identical supplied bytes"))
    return dict(version=1, path_base="data/", files=files,
                family_counts={family: sum(f["family"] == family for f in files)
                               for family in sorted({f["family"] for f in files})},
                intentional_duplicate_sets=duplicates,
                provenance={
                    "archive": "docs/originals/dea-course-v5.dbc",
                    "relationships": "Command-source token matches; not execution verification",
                    "archived_outputs": "Excluded: notebook results are historical, not local inputs",
                    "external_state": "Cloud storage, catalogs, tables, checkpoints and JDBC databases "
                                      "are external state, not supplied local datasets"})


def render(catalog):
    lines = ["# Supplied data catalog", "",
             "Generated by `python3 scripts/maintenance/catalog_data.py`; verify with `--check`.",
             "Paths below are relative to `data/`. SHA-256 and schema hints are in `catalog.json`.",
             "", "## Summary", ""]
    lines += [f"- {family}: {count} files" for family, count in catalog["family_counts"].items()]
    lines += [f"- Total: {len(catalog['files'])} supplied files (README/catalogs excluded).",
              "- Record counts count valid JSON values or CSV/TSV data rows; unknown is `—`.",
              "- JSON schema hints describe valid records only; nested objects/arrays are not flattened.",
              "", "## Provenance and lessons", ""]
    lines += [f"- {value}" for value in catalog["provenance"].values()]
    lines += ["- Per-file lesson paths and matching evidence are listed in JSON; no source or credentials are emitted.",
              "", "## Known issues and intentional duplication", "",
              "- Payments are headerless: columns `_c0`–`_c4`, never a consumed header.",
              "- Refunds SQL is setup for an external database, not a local extract. Its line 6 "
              "`NOT NULL.` typo is preserved; root copy: `scripts/sql/refunds_azure_sql_ddl.sql`."]
    for entry in catalog["files"]:
        if entry["malformed_line_numbers"]:
            lines.append(f"- `{entry['path']}`: malformed JSONL lines "
                         f"{entry['malformed_line_numbers']} (of {entry['nonblank_lines']} nonblank lines).")
    for group in catalog["intentional_duplicate_sets"]:
        lines.append("- " + group["reason"] + ": " + ", ".join(f"`{p}`" for p in group["paths"]))
    lines += ["", "## Per-file inventory", "",
              "| Path | Bytes | Format | Valid records | Columns / image size | Lesson matches |",
              "| --- | ---: | --- | ---: | --- | ---: |"]
    for entry in catalog["files"]:
        hint = ", ".join(entry["columns"])
        if entry["format"] == "png":
            hint = f"{entry['schema_hints']['width']} × {entry['schema_hints']['height']}"
        records = entry["records"] if entry["records"] is not None else "—"
        lines.append(f"| `{entry['path']}` | {entry['bytes']} | {entry['format']} | "
                     f"{records} | {hint} | {len(entry['lessons'])} |")
    return "\n".join(lines) + "\n"


def generated(root):
    catalog = build(root)
    return {"catalog.json": json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
            "catalog.md": render(catalog)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for name, content in generated(ROOT).items():
        target = ROOT / "data" / name
        if args.check:
            if not target.exists() or target.read_bytes() != content.encode("utf-8"):
                mismatches.append(name)
        else:
            target.write_bytes(content.encode("utf-8"))
    if mismatches:
        print("Catalog differs: " + ", ".join(mismatches))
        return 1
    print("Catalog is current." if args.check else "Generated data/catalog.json and data/catalog.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
