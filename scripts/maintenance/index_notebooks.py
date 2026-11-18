#!/usr/bin/env python3
"""Build a local, course-ordered notebook navigation index without execution."""
import argparse
import json
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = [
    ("dea01-databricks-lakehouse-platform", "Platform and notebooks", "52–94"),
    ("dea02-unity-catalog", "Unity Catalog", "95–117"),
    ("dea03-etl-with-apache-spark", "Batch ETL: SQL and Python", "118–165"),
    ("dea03-etl-with-apache-spark-streaming", "Streaming and Auto Loader", "166–200"),
    ("dea04-delta-lake", "Delta Lake", "201–223"),
    ("dea05-databricks-jobs", "Jobs", "225–236"),
    ("dea06-delta-live-tables", "Declarative pipelines (archived DLT)", "237–304"),
    ("dea08-delta-sharing-and-lakehouse-federation", "Sharing and federation", "381–405"),
    ("dea09-data-security", "Data security", "308–345"),
]


def render():
    lines = ["# Notebook index", "",
             "Read in original course section order. Page ranges refer to the V7 lecture PDF;",
             "notebooks come from V5. SQL/Python alternatives are both retained.", "",
             "All results are archived. No course code was executed.", ""]
    for folder, title, pages in SECTIONS:
        lines += [f"## {title}", "", f"Lecture PDF pages: {pages}.", ""]
        for path in sorted((ROOT / "notebooks/course" / folder).rglob("*.ipynb")):
            relative = path.relative_to(ROOT).as_posix()
            lines.append(f"- [{path.stem}](../{quote(relative, safe='/')})")
        lines.append("")
    lines += ["## Additional references", "",
              "The archive's Databricks SQL section is empty (slides 305–307).",
              "Performance material is primarily in slides 346–380.", "",
              "- [Databricks Connect report](../notebooks/db-connect/companies_report.ipynb)",
              "- [Bundle demo](../notebooks/bundle-demo/dab_demo_notebook.ipynb)", "",
              "## Jobs archive aliases", ""]
    manifest = json.loads((ROOT / "docs/conversion-manifest.json").read_text())
    for entry in manifest["notebooks"]:
        for alias in entry["aliases"]:
            lines.append(f"- `{alias['member']}` → "
                         f"[canonical notebook](../{quote(entry['output'], safe='/')})")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    target = ROOT / "docs/notebook-index.md"
    text = render()
    if args.check:
        good = target.exists() and target.read_text() == text
        print("Notebook index is current." if good else "Notebook index differs.")
        return 0 if good else 1
    target.write_text(text, encoding="utf-8")
    print("Generated docs/notebook-index.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
