#!/usr/bin/env python3
"""Convert archived DBC exports without executing code (stdlib only)."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pretty(value):
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def markdown(text, metadata=None):
    return {"cell_type": "markdown", "metadata": metadata or {}, "source": text}


def fenced(text, language=""):
    fence = "`" * max(3, max((len(x) + 1 for x in re.findall(r"`+", text)), default=3))
    return f"{fence}{language}\n{text}\n{fence}"


def text_output(text):
    return {"output_type": "display_data", "metadata": {}, "data": {"text/plain": text}}


def render_result(result):
    """Render every result, retaining unrecognized payloads visibly as JSON."""
    if result is None:
        return []
    if not isinstance(result, dict):
        return [text_output(pretty(result))]
    kind, data = result.get("type"), result.get("data")
    if kind == "listResults" and isinstance(data, list):
        return ([out for item in data for out in render_result(item)]
                if data else [text_output("Archived result list: empty.")])
    if kind == "table":
        schema = result.get("schema", [])
        if isinstance(schema, dict):
            schema = schema.get("fields", schema)
        if isinstance(schema, list):
            columns = [str(x.get("name", i)) if isinstance(x, dict) else str(x)
                       for i, x in enumerate(schema)]
        elif isinstance(schema, dict):
            columns = list(schema)
        else:
            columns = []
        rows = data if isinstance(data, list) else None
        if rows is None:
            return [text_output("Archived table:\n" + pretty(result))]
        lines = ["Archived table" + (" (empty)" if not rows else "") + ":"]
        if columns:
            lines.append("\t".join(columns))
        for row in rows:
            values = ([row.get(k) for k in columns] if isinstance(row, dict) and columns
                      else row if isinstance(row, list) else [row])
            lines.append("\t".join(pretty(v) if isinstance(v, (dict, list)) else str(v)
                                   for v in values))
        return [text_output("\n".join(lines))]
    if kind == "mimeBundle" and isinstance(data, dict):
        bundle = {}
        for mime, value in data.items():
            if mime.startswith(("text/", "image/")) or mime == "application/json":
                bundle[mime] = value
        outputs = []
        if bundle:
            outputs.append({"output_type": "display_data", "metadata": {}, "data": bundle})
        unknown = {k: v for k, v in data.items() if k not in bundle}
        if unknown or not bundle:
            outputs.append(text_output("Archived MIME payload:\n" + pretty(unknown or data)))
        return outputs
    if kind in ("ansi", "text", "html", "htmlSandbox") and isinstance(data, str):
        mime = "text/html" if kind in ("html", "htmlSandbox") else "text/plain"
        return [{"output_type": "display_data", "metadata": {}, "data": {mime: data}}]
    return [text_output("Unsupported archived result (preserved):\n" + pretty(result))]


def has_populated_table(result):
    """Recognize saved table rows, including nested Databricks result lists."""
    if not isinstance(result, dict):
        return False
    data = result.get("data")
    if result.get("type") == "table":
        return isinstance(data, list) and bool(data)
    return (result.get("type") == "listResults" and isinstance(data, list)
            and any(has_populated_table(item) for item in data))


def command_cells(command, index, language):
    source = command.get("command", "")
    metadata = {"archived_databricks": {"original_array_index": index,
                "guid": command.get("guid"), "position": command.get("position"),
                "language": language, "original_command": source,
                "original_results": command.get("results"),
                "original_errors": {k: v for k, v in command.items()
                                    if "error" in k.lower()}}}
    magic = re.match(r"^\s*%([\w-]+)[^\S\n]*(?:\n)?", source)
    md = magic and magic.group(1).lower() in ("md", "md-sandbox")
    runnable = language.lower() == "python" and not magic
    if magic and magic.group(1).lower() == "python":
        runnable = True
        code = source[magic.end():]
    else:
        code = source
    outputs = render_result(command.get("results"))
    errors = metadata["archived_databricks"]["original_errors"]
    visible_errors = {k: v for k, v in errors.items() if v}
    if command.get("error") or command.get("errorSummary"):
        outputs.append(text_output("Historical archived error:\n" + pretty(visible_errors)))
    if md:
        cell = markdown(source[magic.end():], metadata)
    elif runnable:
        return [{"cell_type": "code", "metadata": metadata, "source": code,
                 "execution_count": None, "outputs": outputs}]
    else:
        label = magic.group(1).lower() if magic else language.lower()
        cell = markdown("Archived Databricks source — shown for reading, not Python execution.\n\n"
                        + fenced(source, label), metadata)
    cells = [cell]
    if outputs:
        # Markdown cells cannot contain notebook outputs; a source-free code cell
        # carries the original display payloads without pretending SQL is Python.
        cells.append({"cell_type": "code", "metadata": {"archived_output_only": True},
                      "source": "# Archived output only; no computation.",
                      "execution_count": None, "outputs": outputs})
    return cells


def convert(document, provenance):
    language = document.get("language", "python")
    intro = ("# Archived Databricks example\n\n"
             "Historical source and outputs, not locally executable. Nothing was run during conversion. "
             "Databricks services, datasets and original image assets may be unavailable; image references "
             "are preserved, not downloaded. Outputs and errors are archived, not new execution.")
    cells = [markdown(intro)]
    commands = document.get("commands", [])
    def order(pair):
        try:
            return (float(pair[1].get("position", pair[0])), pair[0])
        except (ValueError, TypeError):
            return (float(pair[0]), pair[0])
    for index, command in sorted(enumerate(commands), key=order):
        cells.extend(command_cells(command, index, language))
    return {"nbformat": 4, "nbformat_minor": 5,
            "metadata": {"archived_databricks": provenance,
                         "kernelspec": {"display_name": "Python 3", "language": "python",
                                        "name": "python3"},
                         "language_info": {"name": "python"}},
            "cells": [dict(cell, id=f"archive-{i:04d}") for i, cell in enumerate(cells)]}


def members(path):
    records = []
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            raw = archive.read(name)
            try:
                doc = json.loads(raw)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(doc, dict) and isinstance(doc.get("commands"), list):
                records.append((name, raw, doc))
    return records


def resolve_archive(name):
    for path in (Path("docs/originals") / name, Path(name)):
        if path.exists():
            return path
    raise FileNotFoundError(name)


def guarded(path, overwrite):
    if not path.exists():
        return
    if path.suffix == ".ipynb":
        existing = json.loads(path.read_text())
        if existing.get("metadata", {}).get("learning_enriched") or any(
                c.get("metadata", {}).get("learning_enriched") for c in existing.get("cells", [])):
            raise ValueError(f"Refusing to overwrite learning_enriched notebook: {path}")
    if not overwrite:
        raise FileExistsError(f"Use --overwrite to replace {path}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--aliases-archive", type=Path)
    parser.add_argument("--output", "--output-dir", dest="output", type=Path,
                        default=Path("notebooks/course"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--check", "--dry-run", dest="check", action="store_true")
    args = parser.parse_args(argv)
    archive = args.archive or resolve_archive("dea-course-v5.dbc")
    records = members(archive)
    aliases_path = args.aliases_archive
    if aliases_path is None:
        try:
            aliases_path = resolve_archive("dea05-databricks-jobs.dbc")
        except FileNotFoundError:
            pass
    aliases = members(aliases_path) if aliases_path else []
    archive_hash = digest(archive.read_bytes())
    if args.sample:
        predicates = [
            lambda d: d.get("language") == "python",
            lambda d: d.get("language") == "sql" and any(
                has_populated_table(c.get("results")) for c in d["commands"]),
            lambda d: any(re.match(r"\s*%(sql|sh|fs|run|scala)", c.get("command", ""))
                          for c in d["commands"]),
        ]
        selected = []
        for predicate in predicates:
            match = next((r for r in records if r not in selected and predicate(r[2])), None)
            if match is None:
                raise ValueError("Archive lacks a required representative sample")
            selected.append(match)
        records = selected
    plan, entries = [], []
    for name, raw, doc in records:
        parts = PurePosixPath(name).parts
        if ".." in parts or PurePosixPath(name).is_absolute():
            raise ValueError("Unsafe archive member path")
        # The DBC's top-level course directory is a container, not a section.
        relative = Path(*parts[1:] if len(parts) > 1 else parts).with_suffix(".ipynb")
        target = args.output / relative
        source_commands = [c.get("command") for c in doc["commands"]]
        matched = [{"archive": str(aliases_path), "archive_sha256": digest(aliases_path.read_bytes()),
                    "member": an, "member_sha256": digest(ar)}
                   for an, ar, ad in aliases
                   if [c.get("command") for c in ad["commands"]] == source_commands
                   and [c.get("results") for c in ad["commands"]] ==
                       [c.get("results") for c in doc["commands"]]]
        provenance = {"archive": str(archive), "archive_sha256": archive_hash,
                      "member": name, "member_sha256": digest(raw), "aliases": matched}
        notebook = convert(doc, provenance)
        entry = dict(provenance, output=str(target), command_count=len(doc["commands"]),
                     cell_count=len(notebook["cells"]),
                     output_count=sum(len(c.get("outputs", [])) for c in notebook["cells"]))
        entries.append(entry)
        plan.append((target, pretty(notebook) + "\n"))
    if len({p for p, _ in plan}) != len(plan):
        raise ValueError("Duplicate notebook destination")
    if args.manifest:
        plan.append((args.manifest, pretty({"notebooks": entries}) + "\n"))
    for path, _ in plan:
        guarded(path, args.overwrite)
    if not args.check:
        for path, content in plan:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"{'Checked' if args.check else 'Converted'} {len(entries)} notebooks; no code executed.")


if __name__ == "__main__":
    main()
