#!/usr/bin/env python3
"""Add deterministic, source-aware reading notes without executing archived lessons."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
VERSION = 1
TEACHING_EXAMPLES = {
    "join": "Two left rows and three right rows with the same matching key yield six joined rows.",
    "json-array": "Exploding an array [a, b] yields two rows for that input row.",
    "aggregate": "Grouping three orders for one customer by customer yields one customer-level group, not three order-level rows.",
    "scd": "For a customer address change, SCD1 replaces the address; SCD2 can keep the old and new address in separate validity intervals.",
    "schema": "Parsing a numeric field from an incompatible string can fail or yield null depending on parsing mode; inspect the declared schema and error policy.",
    "window": "Ranking two rows in one partition gives two ranked rows; grouping that partition would instead reduce its grain.",
}

# Patterns examine source locally; only these fixed explanations enter new prose.
OPERATIONS = [
    ("join", r"\bjoin\b|\.join\(", "Check join keys and cardinality on both inputs; unmatched keys and duplicate keys affect nulls and row counts in the joined output."),
    ("merge", r"\bmerge\b", "MERGE matches source rows to target keys and applies matched/unmatched actions. Verify source-key uniqueness and distinguish updates from inserts."),
    ("window", r"\bover\s*\(|Window\.|row_number|lag\(", "Window partition keys define independent groups; ordering and ties determine rankings or prior-row values without necessarily reducing row count."),
    ("stream", r"readStream|writeStream|\bstream\s*\(|streaming", "A streaming input is processed incrementally, not as a fixed batch. Interpret displayed rows as historical observations, not proof that a stream is currently running."),
    ("autoloader", r"cloudFiles|auto.loader", "Auto Loader discovers arriving files. File format/options and schema tracking determine parsing; discovery is distinct from downstream transformations."),
    ("checkpoint", r"checkpoint", "Checkpoint state tracks progress and recovery. Reusing versus deleting a checkpoint changes replay behavior; no checkpoint state is supplied locally."),
    ("schema", r"\bschema\b|from_json|inferSchema|schemaEvolution", "Compare declared or inferred field types with raw input. Parsing, schema evolution and rescued/corrupt records can produce nulls or additional columns rather than clean typed rows."),
    ("security", r"\bgrant\b|\bmask\b|row.filter|current_user|is_account_group_member|credential|external.location|governed|\babac\b", "Access depends on the executing identity, grants, filters/masks and storage configuration. A saved result is not evidence that another identity has the same access; credentials are not reproduced here."),
    ("vacuum", r"\bvacuum\b", "VACUUM removes eligible unreferenced files, not current table rows. Retention protects readers and time travel; aggressive retention can permanently remove historical versions."),
    ("ctas", r"\bcreate\b[\s\S]*?\bas\s+select\b|saveAsTable", "Table creation materializes a query/DataFrame into a destination. Distinguish its stored schema and rows from a view and check whether replacement overwrites existing state."),
    ("scd", r"apply.changes|create_auto_cdc|stored.as.scd|\bscd\b", "Change application uses keys and sequencing to resolve events. SCD type 1 replaces current values; type 2 retains validity intervals. Verify the actual configured type and event ordering."),
    ("aggregate", r"\bgroup\s+by\b|groupBy|\.agg\(", "Grouping changes the output grain to one row per group. Check null handling, counts versus distinct counts, and whether joins inflated measures before aggregation."),
    ("json-array", r"explode|from_json|get_json_object|json_tuple|transform\(|filter\(", "JSON extraction and array operations change structure: parsing creates typed values, while explode can create multiple rows per input. Inspect missing fields, null arrays and empty arrays."),
    ("write", r"\binsert\b|\.write\b|overwrite|copy\s+into", "This operation changes persistent state. Identify append, overwrite or incremental-copy semantics before rerunning; archived output does not establish the current destination contents."),
    ("delta-history", r"time.travel|version.as.of|timestamp.as.of|describe.history|_delta_log|restore", "Delta versions describe committed table state. Historical reads require retained log and data files; saved history is not a locally available Delta table."),
    ("optimize", r"optimize|zorder|cluster\s+by", "Compaction and clustering change physical file layout for pruning, not logical query results. Compare file statistics rather than assuming fewer result rows."),
    ("jdbc", r"jdbc|foreign.catalog|create.connection", "The input is an external database connection/table. Local setup SQL is not a database extract; connectivity, credentials and remote state are unavailable here."),
    ("udf", r"create.*function|\budf\b", "A function maps arguments to a result according to its declared types. Check null handling and compare built-in expressions before relying on per-row function evaluation."),
    ("utilities", r"dbutils|%fs|%sh|%run|os\.environ|getArgument", "These commands depend on notebook/runtime context, files, widgets or process state. Interpret listings and printed values as archived observations; do not assume local paths or services exist."),
    ("profiling", r"describe|summary\(|\.count\(|\bcount\(|display\(|\bselect\b", "Read the selected columns and output grain before interpreting the saved result. Counts, nulls and samples describe the archived input state, not a newly executed validation."),
]


def source(cell):
    value = cell.get("metadata", {}).get("archived_databricks", {}).get(
        "original_command", cell.get("source", ""))
    return "".join(value) if isinstance(value, list) else value


def operations(text):
    return [(name, note) for name, pattern, note in OPERATIONS
            if re.search(pattern, text, re.I)]


def lesson_summary(text, found):
    """Describe evidenced operations without copying source literals or credentials."""
    labels = {
        "join": "Relate inputs by keys and explain the resulting cardinality.",
        "merge": "Trace key-based changes from incoming records into a persistent target.",
        "stream": "Follow incremental ingestion from discovery to persisted results.",
        "autoloader": "Separate file discovery, parsing and schema tracking.",
        "schema": "Compare raw fields with typed records and parsing failures.",
        "security": "Explain how identity and governance affect visible data and permitted actions.",
        "aggregate": "Identify grouping keys and the business grain of summary measures.",
        "json-array": "Follow nested JSON and arrays as they become columns or rows.",
        "jdbc": "Distinguish external database access from locally supplied setup material.",
        "write": "Trace how source records change persistent destination state.",
        "delta-history": "Relate committed versions to historical table reads and retained files.",
        "vacuum": "Distinguish removal of obsolete physical files from logical row deletion.",
        "optimize": "Explain physical layout changes without confusing them with logical transformations.",
        "utilities": "Distinguish runtime configuration and notebook orchestration from data transformation.",
        "profiling": "Interpret selected fields, samples and counts at their actual output grain.",
        "ctas": "Distinguish query results from materialized table state.",
        "udf": "Trace function arguments, declared return types and row-level results.",
        "window": "Explain ordered calculations within partitions without reducing row grain.",
        "scd": "Trace sequenced changes into current-state or history-preserving records.",
        "checkpoint": "Relate progress state to recovery and replay behavior.",
    }
    summaries = [labels[name] for name, _ in found if name in labels]
    if summaries:
        return "\n".join("- " + item for item in summaries)
    if re.search(r"\bprint\b|displayHTML|display", text, re.I):
        return "- Follow inline values into printed or rendered notebook observations; distinguish presentation from persisted data."
    if re.search(r"%md|#|markdown", text, re.I):
        return "- Read the lesson's notebook workflow and distinguish explanatory Markdown from executable commands and saved observations."
    return "- Trace inline expressions and notebook setup in source order; distinguish returned values from persisted data and runtime state."


def safe_targets(cells):
    """Only SQL object identifiers, never quoted connection strings or options."""
    commands = []
    python_names = []
    identifier = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){0,2}"
    for cell in cells:
        if cell.get("metadata", {}).get("archived_output_only"):
            continue
        text = source(cell)
        archive = cell.get("metadata", {}).get("archived_databricks", {})
        if re.match(r"\s*%md(?:-sandbox)?\b", text):
            continue
        if not archive and cell.get("cell_type") != "code":
            continue
        text = re.sub(r"/\*[\s\S]*?\*/|--[^\n]*|#[^\n]*", " ", text)
        python_names.extend(re.findall(
            r"\b(?:spark\.table|saveAsTable)\(\s*['\"](" + identifier + r")['\"]\s*\)", text))
        if (re.match(r"\s*%sql\b", text)
                or archive.get("language", "").lower() == "sql"
                or re.match(r"\s*(?:SELECT|WITH|CREATE|INSERT|MERGE|UPDATE|DELETE|ALTER|DROP|TRUNCATE)\b", text, re.I)):
            commands.append(text)
    text = "\n".join(commands)
    stripped = re.sub(r"'(?:''|[^'])*'|\"(?:\\.|[^\"\\])*\"", " ", text)
    names = re.findall(
        r"\b(?:from|join|insert\s+into|merge\s+into|update|"
        r"(?:create(?:\s+or\s+replace)?|alter|drop|truncate)\s+table(?:\s+if\s+(?:not\s+)?exists)?)\s+"
        r"(" + identifier + r")\b(?!\s*\()",
        stripped, re.I)
    blocked = {"if", "as", "select", "not", "function", "delta", "csv", "json", "parquet"}
    return sorted({name for name in names + python_names if name.lower() not in blocked
                   and not re.search(r"password|secret|token|credential", name, re.I)})


def fenced(text, language=""):
    fence = "`" * max(3, max((len(x) + 1 for x in re.findall(r"`+", text)), default=3))
    return f"{fence}{language}\n{text}\n{fence}"


def learning_cell(key, text, **extra):
    return dict(cell_type="markdown", id="learning-" + key,
                metadata={"learning_enriched": True, "enrichment_version": VERSION},
                source="## Learning notes — " + text, **extra)


def snapshot_entries(catalog, member, text):
    """Require both catalog attribution and explicit entity/lane evidence."""
    selected = []
    low = text.lower()
    for entry in catalog.get("files", []):
        path = entry["path"]
        parts = Path(path).parts
        family = entry.get("family", parts[0])
        dataset = entry.get("dataset", parts[1] if len(parts) > 2 else parts[0])
        related = member in entry.get("lessons", [])
        explicit = (family.lower() in low and
                    re.search(r"(?<![\w])" + re.escape(dataset.lower()) + r"(?![\w])", low))
        if (related and explicit) or path.lower() in low:
            selected.append(entry)
    return sorted(selected, key=lambda e: e["path"])


def enrich(notebook, path, root=ROOT, catalog=None):
    original = copy.deepcopy(notebook)
    cells = [c for c in original["cells"] if not c.get("metadata", {}).get("learning_enriched")]
    member = original.get("metadata", {}).get("archived_databricks", {}).get("member", "")
    title = Path(member or path).stem
    texts = [source(c) for c in cells]
    text = "\n".join(texts)
    found = operations(text)
    entries = snapshot_entries(catalog or {}, member, text)
    related_paths = set()
    companies_lesson = (Path(path).stem == "companies_report" or
                        re.search(r"(?:bronze|silver|gold)_companies$", Path(path).stem))
    if companies_lesson:
        for entry in (catalog or {}).get("files", []):
            if entry["path"] in {
                    "top_tech_companies/top_tech_companies_1.csv",
                    "top_tech_companies/top_tech_companies_2.csv"}:
                related_paths.add(entry["path"])
                if not any(item["path"] == entry["path"] for item in entries):
                    entries.append(entry)
        entries.sort(key=lambda item: item["path"])
    intro = (
        f"{title}\n\n### Learning objectives\n"
        f"Follow **{title}** from its source inputs through its operations to the archived results.\n"
        + ("- Explain " + ", ".join(name for name, _ in found) + " as used in this lesson.\n" if found else
           "- Distinguish notebook setup, inline examples and their saved observations.\n")
        + "\n### Source-specific learning focus\n" + lesson_summary(text, found) + "\n"
        + "\n### Input/output interpretation\n"
        "Original source and outputs are preserved unchanged and were not executed. "
        "Saved tables, HTML displays and errors are archived generated outputs, not supplied datasets. "
        "Inline literals are examples already present in the source. "
        "Cloud storage, remote tables, catalogs, services and checkpoints are unavailable locally unless "
        "a supplied snapshot is explicitly listed below; no external input is claimed available.\n")
    targets = safe_targets(cells)
    if targets:
        intro += ("\nSQL relation identifiers referenced in source (inputs and/or destinations; "
                  "not a claim that these objects exist locally): "
                  + ", ".join(f"`{name}`" for name in targets) + ".\n")
    if Path(path).stem == "companies_report":
        intro += "\nThe remote companies table is absent from the supplied inputs; its archived results cannot be independently reproduced from local data.\n"
    if "bundle" in str(path).lower():
        intro += "\nThe bundle demo uses inline example data; archived HTML displays show historical rendering, not an external input or a new execution.\n"
    added = [learning_cell("overview", intro)]
    snapshot_paths = []
    for entry in entries:
        relative = Path("data") / entry["path"]
        target = (root / relative).resolve()
        if not target.is_relative_to((root / "data").resolve()):
            raise ValueError("Unsafe catalog path")
        if not target.is_file():
            raise FileNotFoundError(relative)
        raw = target.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        heading = f"supplied input snapshot\n\nPath: `{relative.as_posix()}`\n\nSHA-256: `{digest}`\n\n"
        if entry["path"] in related_paths:
            heading += (
                "**Related supplied companies learning input (explicit curated attribution, "
                "not an automatic source-token match):** schema-compatible columns "
                "`company_name,founded_date,country`; not verified to be identical to "
                "the original remote table or landing contents. No execution equivalence "
                "or exact source provenance is claimed.\n\n")
        key = "snapshot-" + hashlib.sha256(str(relative).encode()).hexdigest()[:16]
        if target.suffix.lower() == ".png":
            name = target.name
            cell = learning_cell(key, heading + f"![Supplied image](attachment:{name})",
                                 attachments={name: {"image/png": base64.b64encode(raw).decode("ascii")}})
        else:
            cell = learning_cell(key, heading + "Complete supplied text (not generated output):\n\n"
                                 + fenced(raw.decode("utf-8"), target.suffix.lstrip(".")))
        added.append(cell)
        snapshot_paths.append(relative.as_posix())
    corrections = []
    if re.search(r"payments", text, re.I) and re.search(r"header[^\n]{0,30}true", text, re.I):
        corrections.append("Payments files are headerless. Corrective commentary: header=true consumes the first payment as a header; use header=false with explicit columns in a separate corrected experiment.")
    if any(e.get("malformed_line_numbers") for e in entries):
        corrections.append("Supplied orders JSONL includes malformed lines. Corrective commentary: inspect corrupt-record handling before interpreting parsed row counts; the complete raw snapshot above intentionally preserves these defects.")
    if "refund" in text.lower():
        corrections.append("Refunds setup SQL contains a NOT NULL. typo: the period must be removed in a separate corrected copy before database setup. The supplied SQL is setup, not remote Refunds table contents.")
    if corrections:
        added.append(learning_cell("corrections", "corrective commentary (originals unchanged)\n\n" + "\n\n".join(corrections)))
    result = added[:]
    annotations = []
    for index, cell in enumerate(cells):
        code = source(cell)
        is_command = bool(cell.get("metadata", {}).get("archived_databricks")) or cell.get("cell_type") == "code"
        if is_command and not re.match(r"\s*%md", code) and not cell.get("metadata", {}).get("archived_output_only"):
            notes = operations(code)
            if notes:
                result.append(learning_cell(f"operation-{index:04d}",
                    "before source operation\n\n" + "\n\n".join(
                        f"**{name}**: {note}" +
                        ("\n\n**Unexecuted teaching example (illustrative, not an archived or generated result):** "
                         + TEACHING_EXAMPLES[name] if name in TEACHING_EXAMPLES else "")
                        for name, note in notes)))
                annotations.append({"original_cell_index": index, "operations": [n for n, _ in notes]})
        result.append(cell)
    original["cells"] = result
    original.setdefault("metadata", {})["learning_enriched"] = True
    report = dict(path=str(path), reviewed_lesson_title=title,
                  operation_annotations=annotations, snapshot_paths=snapshot_paths,
                  related_input_attributions=[
                      {"path": "data/" + item,
                       "attribution": "curated related companies learning input",
                       "schema_compatible": True,
                       "original_remote_contents_verified": False,
                       "automatic_source_match": False}
                      for item in sorted(related_paths)],
                  external_input_claim=False, enriched_cell_count=len(result) - len(cells))
    return original, report


def canonical_paths(root):
    paths = set((root / "notebooks/course").rglob("*.ipynb"))
    for directory in ("db-connect", "bundle-demo"):
        paths.update((root / "notebooks" / directory).rglob("*.ipynb"))
    return sorted(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="*", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args(argv)
    catalog_path = ROOT / "data/catalog.json"
    if not catalog_path.exists():
        parser.error("data/catalog.json is required for accurate snapshot attribution")
    catalog = json.loads(catalog_path.read_text())
    paths = args.notebooks or canonical_paths(ROOT)
    reports, stale = [], []
    for path in paths:
        before = json.loads(path.read_text())
        after, report = enrich(before, path, ROOT, catalog)
        reports.append(report)
        if before != after:
            stale.append(str(path))
            if not args.check:
                path.write_text(json.dumps(after, indent=2, ensure_ascii=False) + "\n")
    if args.output and not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"version": VERSION, "notebooks": reports}, indent=2) + "\n")
    print(f"{len(paths)} notebooks reviewed; {len(stale)} {'stale' if args.check else 'updated'}; no code executed.")
    return int(args.check and bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
