#!/usr/bin/env python3
"""Read-only repository evidence checks; never execute notebook code."""
import argparse
import base64
import contextlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

if __package__:
    from . import convert_dbc
else:
    import convert_dbc

ROOT = Path(__file__).resolve().parents[2]


def text(value):
    return isinstance(value, str) or (
        isinstance(value, list) and all(isinstance(x, str) for x in value))


def notebook_errors(nb):
    """Validate the actual serialized shape, even without optional nbformat."""
    errors = []
    def require(ok, label):
        if not ok:
            errors.append(label)
    if not isinstance(nb, dict):
        return ["notebook object"]
    require(nb.get("nbformat") == 4, "nbformat")
    minor = nb.get("nbformat_minor")
    require(type(minor) is int and minor >= 0, "minor version")
    require(isinstance(nb.get("metadata"), dict), "metadata")
    cells = nb.get("cells")
    if not isinstance(cells, list):
        return errors + ["cells"]
    ids = set()
    for cell in cells:
        if not isinstance(cell, dict):
            errors.append("cell object")
            continue
        kind = cell.get("cell_type")
        require(kind in ("code", "markdown", "raw"), "cell type")
        require(text(cell.get("source")), "cell source")
        require(isinstance(cell.get("metadata"), dict), "cell metadata")
        if (type(minor) is int and minor >= 5) or "id" in cell:
            ident = cell.get("id")
            valid = isinstance(ident, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", ident)
            require(bool(valid) and ident not in ids, "cell id")
            if valid:
                ids.add(ident)
        if kind != "code":
            require("outputs" not in cell and "execution_count" not in cell, "noncode outputs")
            continue
        count = cell.get("execution_count")
        require("execution_count" in cell and (count is None or type(count) is int), "execution count")
        outputs = cell.get("outputs")
        if not isinstance(outputs, list):
            errors.append("outputs")
            continue
        for out in outputs:
            if not isinstance(out, dict):
                errors.append("output object")
                continue
            typ = out.get("output_type")
            require(typ in ("stream", "display_data", "execute_result", "error"), "output type")
            if typ == "stream":
                require(out.get("name") in ("stdout", "stderr") and text(out.get("text")), "stream")
            elif typ == "error":
                require(isinstance(out.get("ename"), str) and isinstance(out.get("evalue"), str)
                        and isinstance(out.get("traceback"), list)
                        and all(isinstance(x, str) for x in out["traceback"]), "error output")
            elif typ in ("display_data", "execute_result"):
                data = out.get("data")
                require(isinstance(data, dict) and isinstance(out.get("metadata"), dict), "MIME bundle")
                if isinstance(data, dict):
                    for mime, value in data.items():
                        require(isinstance(mime, str) and "/" in mime, "MIME key")
                        if isinstance(mime, str) and not mime.endswith("+json") and mime != "application/json":
                            require(text(value), "MIME value")
                if typ == "execute_result":
                    require(type(out.get("execution_count")) is int, "result count")
    if not errors:
        try:
            import nbformat
        except ImportError:
            pass
        else:
            try:
                with contextlib.redirect_stderr(io.StringIO()):
                    nbformat.validate(nb)
            except Exception:
                errors.append("optional nbformat schema")
    return errors


def original_cells(nb):
    return [c for c in nb["cells"] if not c.get("metadata", {}).get("learning_enriched")]


def historical_error(command):
    """Error-detail scaffolding alone does not indicate a failed command."""
    return bool(command.get("error") or command.get("errorSummary"))


def preserved_cells(actual, expected):
    """Only the enrichment flag may be added to original cell metadata."""
    cells = original_cells(actual)
    cleaned = []
    for cell in cells:
        cell = dict(cell)
        cell["metadata"] = dict(cell.get("metadata", {}))
        cell["metadata"].pop("learning_enriched", None)
        cleaned.append(cell)
    return cleaned == expected["cells"]


def compact_payload_errors(nb, path, raw, provenance):
    """Compare external exact bytes and visible source against the immutable archive."""
    errors = []
    meta = nb.get("metadata", {}).get("archived_databricks", {})
    try:
        payload_raw = (path.parent / meta["payload_ref"]).read_bytes()
        payload = json.loads(payload_raw)
        if convert_dbc.digest(payload_raw) != meta["payload_sha256"]:
            errors.append("payload checksum")
        if (base64.b64decode(payload["source_base64"], validate=True) != raw
                or payload["document"] != json.loads(raw)
                or payload["provenance"] != provenance):
            errors.append("payload original fidelity")
        expected = convert_dbc.convert(json.loads(raw), provenance, meta["payload_ref"])
        if not preserved_cells(nb, expected):
            errors.append("compact source or output fidelity")
    except (OSError, ValueError, KeyError, TypeError):
        errors.append("missing or invalid external payload")
    return errors


def local_links(path, root):
    content = path.read_text(encoding="utf-8")
    return local_link_errors(content, path, root)


def local_link_errors(content, path, root):
    """Count missing local links in Markdown, including notebook-added cells."""
    content = re.sub(r"```.*?```|~~~.*?~~~", "", content, flags=re.S)
    targets = re.findall(r"!?\[[^\]]*\]\(\s*(<[^>]+>|[^\s)]+)", content)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*(<[^>]+>|\S+)", content, re.M)
    missing = 0
    for target in targets:
        parts = urlsplit(target.strip("<>"))
        if parts.scheme or parts.netloc or not parts.path:
            continue
        destination = (root / unquote(parts.path).lstrip("/") if parts.path.startswith("/")
                       else path.parent / unquote(parts.path))
        if not destination.exists():
            missing += 1
    return missing


def snapshots_valid(nb, root, recorded=None):
    """Check complete embedded bytes, not merely the displayed hash."""
    found = []
    for cell in nb["cells"]:
        if not cell.get("metadata", {}).get("learning_enriched"):
            continue
        source = cell.get("source", "")
        source = "".join(source) if isinstance(source, list) else source
        match = re.search(r"Path: `([^`]+)`\n\nSHA-256: `([0-9a-f]{64})`", source)
        if not match:
            continue
        relative, digest = match.groups()
        target = (root / relative).resolve()
        if not target.is_relative_to((root / "data").resolve()) or not target.is_file():
            return False
        raw = target.read_bytes()
        if convert_dbc.digest(raw) != digest:
            return False
        if target.suffix.lower() == ".png":
            encoded = cell.get("attachments", {}).get(target.name, {}).get("image/png")
            try:
                if base64.b64decode(encoded, validate=True) != raw:
                    return False
            except (ValueError, TypeError):
                return False
        else:
            marker = "Complete supplied text (not generated output):\n\n"
            if marker not in source:
                return False
            block = source.split(marker, 1)[1]
            lines = block.split("\n")
            if len(lines) < 3 or not re.fullmatch(r"`{3,}.*", lines[0]):
                return False
            fence = re.match(r"`+", lines[0])[0]
            if lines[-1] != fence or "\n".join(lines[1:-1]).encode("utf-8") != raw:
                return False
        found.append(relative)
    return len(found) == len(set(found)) and (recorded is None or sorted(found) == sorted(recorded))


def enrichment_errors(nb, report):
    errors = []
    added = [c for c in nb["cells"] if c.get("metadata", {}).get("learning_enriched")]
    if nb.get("metadata", {}).get("learning_enriched") is not True or not added:
        errors.append("missing learning enrichment")
    if report.get("enriched_cell_count") != len(added):
        errors.append("enrichment cell count")
    annotations = report.get("operation_annotations")
    if not isinstance(annotations, list):
        return errors + ["operation annotations"]
    originals = original_cells(nb)
    indexes = []
    for annotation in annotations:
        index = annotation.get("original_cell_index")
        operations = annotation.get("operations")
        if (type(index) is not int or not 0 <= index < len(originals)
                or not isinstance(operations, list) or not operations
                or not all(isinstance(op, str) and op for op in operations)):
            errors.append("operation annotation shape")
        indexes.append(index)
    if len({str(i) for i in indexes}) != len(indexes):
        errors.append("duplicate operation annotation")
    operation_cells = sum("before source operation\n\n" in
                          (c["source"] if isinstance(c["source"], str) else "".join(c["source"]))
                          for c in added)
    if operation_cells != len(annotations):
        errors.append("operation annotation count")
    if not isinstance(report.get("input_paths", report.get("snapshot_paths")), list):
        errors.append("snapshot paths")
    return errors


def validate(root):
    errors, evidence = [], {}
    def check(ok, label):
        if not ok:
            errors.append(label)
    def load(path):
        return json.loads(path.read_text(encoding="utf-8"))
    def safe(name):
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError("unsafe path")
        return path
    for script, key in (("inventory.py", "original_inventory"), ("catalog_data.py", "catalog")):
        result = subprocess.run([sys.executable, str(root / "scripts/maintenance" / script),
                                 *(["--check"] if key == "catalog" else [])],
                                cwd=root, capture_output=True, text=True)
        evidence[key] = result.returncode == 0
        check(result.returncode == 0, key + " failed")
    assets = load(root / "artifacts/metadata/source-map.json")["assets"]
    primary = next(a for a in assets if a["old"] == "dea-course-v5.dbc")
    jobs = next(a for a in assets if a["old"] == "dea05-databricks-jobs.dbc")
    archive = safe(primary["new"])
    records = {name: (raw, doc) for name, raw, doc in convert_dbc.members(archive)}
    aliases = {name: (raw, doc) for name, raw, doc in convert_dbc.members(safe(jobs["new"]))}
    entries = load(root / "artifacts/metadata/conversion-manifest.json")["notebooks"]
    check(len(records) == len(entries) == 69, "primary count")
    check({e["member"] for e in entries} == set(records), "primary membership")
    destinations, seen_members, seen_aliases = set(), set(), set()
    for entry in entries:
        member = entry["member"]
        check(member not in seen_members, "duplicate member")
        seen_members.add(member)
        raw, doc = records[member]
        target = safe(entry["output"])
        check(target not in destinations, "duplicate destination")
        destinations.add(target)
        check(target.is_relative_to(root / "notebooks/course"), "course destination")
        provenance = {k: entry[k] for k in
                      ("archive", "archive_sha256", "member", "member_sha256", "aliases")}
        check(safe(entry["archive"]) == archive and
              entry["archive_sha256"] == convert_dbc.digest(archive.read_bytes()) and
              entry["member_sha256"] == convert_dbc.digest(raw), "primary provenance")
        expected = convert_dbc.convert(doc, provenance)
        nb = load(target)
        if nb.get("metadata", {}).get("archived_databricks", {}).get("presentation_version"):
            check(not compact_payload_errors(nb, target, raw, provenance), "compact payload fidelity")
            expected = convert_dbc.convert(doc, provenance, nb["metadata"]["archived_databricks"]["payload_ref"])
            provenance = dict(provenance, **{
                k: nb["metadata"]["archived_databricks"][k]
                for k in ("payload_ref", "payload_sha256", "presentation_version")})
        check(not notebook_errors(nb), "invalid course notebook")
        check(preserved_cells(nb, expected), "changed original course cells")
        check(nb["metadata"].get("archived_databricks") == provenance, "notebook provenance")
        check(entry["command_count"] == len(doc["commands"]) and
              entry["cell_count"] == len(expected["cells"]) and
              entry["output_count"] == sum(len(c.get("outputs", [])) for c in expected["cells"]),
              "manifest counts")
        expected_aliases = set()
        for name, (alias_raw, alias_doc) in aliases.items():
            if ([c.get("command") for c in doc["commands"]] ==
                [c.get("command") for c in alias_doc["commands"]] and
                [c.get("results") for c in doc["commands"]] ==
                [c.get("results") for c in alias_doc["commands"]]):
                expected_aliases.add(name)
        check({a["member"] for a in entry["aliases"]} == expected_aliases
              and len(entry["aliases"]) == len(expected_aliases), "alias membership")
        for alias in entry["aliases"]:
            alias_raw, _ = aliases[alias["member"]]
            check(safe(alias["archive"]) == safe(jobs["new"]) and
                  alias["archive_sha256"] == convert_dbc.digest(safe(jobs["new"]).read_bytes())
                  and alias["member_sha256"] == convert_dbc.digest(alias_raw), "alias provenance")
            seen_aliases.add(alias["member"])
    check(len(aliases) == len(seen_aliases) == 3, "alias coverage")
    standalone = [a for a in assets if "study_copy" in a]
    check(len(standalone) == 2, "standalone count")
    for asset in standalone:
        target = safe(asset["study_copy"])
        check(target not in destinations, "duplicate standalone")
        destinations.add(target)
        nb = load(target)
        check(not notebook_errors(nb), "invalid standalone notebook")
        standalone_meta = nb.get("metadata", {}).get("archived_standalone")
        if standalone_meta:
            original_raw = safe(asset["new"]).read_bytes()
            provenance = {k: standalone_meta[k] for k in ("member", "original", "member_sha256")}
            try:
                payload_raw = (target.parent / standalone_meta["payload_ref"]).read_bytes()
                payload = json.loads(payload_raw)
                check(convert_dbc.digest(payload_raw) == standalone_meta["payload_sha256"],
                      "standalone payload checksum")
                check(base64.b64decode(payload["source_base64"], validate=True) == original_raw
                      and payload["document"] == json.loads(original_raw)
                      and payload["provenance"] == provenance, "standalone payload fidelity")
                expected = convert_dbc.compact_standalone(original_raw, provenance,
                                                        standalone_meta["payload_ref"])
                check(preserved_cells(nb, expected), "changed compact standalone source or outputs")
            except (OSError, ValueError, KeyError, TypeError):
                check(False, "missing standalone payload")
        else:
            check(preserved_cells(nb, load(safe(asset["new"]))), "changed standalone cells")
    actual = {p.resolve() for p in (root / "notebooks").rglob("*.ipynb")
              if not any(x in ("samples", ".ipynb_checkpoints") for x in p.parts)}
    check(len(destinations) == 71 and actual == destinations, "canonical study coverage")
    evidence.update(primary=len(records), aliases=len(seen_aliases), canonical=len(destinations))
    commands = [c for _, doc in records.values() for c in doc["commands"]]
    command_count = len(commands)
    result_count = sum(c.get("results") is not None for c in commands)
    error_count = sum(historical_error(c) for c in commands)
    evidence.update(original_commands=command_count, result_containers=result_count,
                    historical_errors=error_count)
    check((command_count, result_count, error_count) == (690, 373, 3), "historical evidence counts")
    reports = load(root / "artifacts/metadata/enrichment-report.json")["notebooks"]
    snapshot_records = {safe(item["path"]): item for item in reports}
    check(len(reports) == len(snapshot_records) == 71 and set(snapshot_records) == destinations,
          "enrichment report coverage")
    enriched = snapshot_count = input_reference_count = notebook_broken_links = 0
    for target in destinations:
        nb = load(target)
        item = snapshot_records.get(target, {})
        check(not enrichment_errors(nb, item), "enrichment report consistency")
        paths = item.get("input_paths", item.get("snapshot_paths", []))
        if "input_paths" in item:
            input_reference_count += len(paths)
            check(all(safe(p).is_file() for p in paths), "missing linked original input")
            check(not any(c.get("attachments") for c in nb["cells"]
                          if c.get("metadata", {}).get("learning_enriched")), "embedded input image")
        else:
            check(snapshots_valid(nb, root, paths), "snapshot completeness or hash")
            snapshot_count += len(paths)
        for cell in nb["cells"]:
            if (cell.get("cell_type") == "markdown"
                    and (cell.get("metadata", {}).get("learning_enriched")
                         or cell.get("id") in ("archive-0000", "standalone-0000"))):
                source = cell["source"]
                notebook_broken_links += local_link_errors(
                    "".join(source) if isinstance(source, list) else source, target, root)
        enriched += nb.get("metadata", {}).get("learning_enriched") is True
    check(notebook_broken_links == 0, "missing local notebook links")
    evidence.update(enriched_notebooks=enriched, input_references=input_reference_count,
                    embedded_input_snapshots=snapshot_count,
                    broken_notebook_links=notebook_broken_links)
    check(enriched == 71, "enriched notebook coverage")
    broken = 0
    for path in root.rglob("*.md"):
        if any(x in (".git", ".venv", ".work", "node_modules") for x in path.parts):
            continue
        if path.is_relative_to(root / "docs/originals"):
            continue
        broken += local_links(path, root)
    check(broken == 0, "missing local Markdown links")
    evidence["broken_links"] = broken
    return {"ok": not errors, "evidence": evidence, "errors": errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, nargs="?", const=Path("artifacts/metadata/validation-report.json"))
    args = parser.parse_args(argv)
    try:
        report = validate(ROOT)
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        report = {"ok": False, "evidence": {}, "errors": ["missing or invalid validation input"]}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("Validation " + ("passed" if report["ok"] else "failed") + ": "
          + json.dumps(report["evidence"], sort_keys=True))
    for error in report["errors"]:
        print("- " + error)
    return int(not report["ok"])


if __name__ == "__main__":
    sys.exit(main())
