#!/usr/bin/env python3
"""Stage compact study copies, preserving immutable originals; never execute code."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath

import convert_dbc as converter
import enrich_notebooks as enricher
import validate_repository as validator

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ("09. Data Profiling.sql", "03. Extract Orders Data - Complex JSON as Text.sql",
           "04. Extract Memberships Data - Images.sql", "18. Join Customer Address.sql")


def preflight_existing(target, baselines):
    """Never erase source/output edits, even with explicit installation consent."""
    if not target.is_file():
        raise ValueError(f"Missing canonical notebook: {target}")
    existing = json.loads(target.read_text())
    if not any(validator.preserved_cells(existing, baseline) for baseline in baselines):
        raise ValueError(f"Refusing learner-modified notebook: {target}")


def generate(output, samples=True, check=False, install=False):
    output = output.resolve()
    if install:
        output, samples = ROOT.resolve(), False
    elif not output.is_relative_to((ROOT / ".work").resolve()):
        raise ValueError("Stage under .work; canonical migration requires separate approval")
    archive = ROOT / "materials/archives/dea-course-v5.dbc"
    catalog = json.loads((ROOT / "data/catalog.json").read_text())
    source_map = json.loads((ROOT / "artifacts/metadata/source-map.json").read_text())
    reports, plan, manifest, preflight = [], [], [], []
    archive_hash = converter.digest(archive.read_bytes())
    jobs = ROOT / "materials/archives/dea05-databricks-jobs.dbc"
    aliases = converter.members(jobs)
    for name, raw, doc in converter.members(archive):
        if samples and PurePosixPath(name).name not in SAMPLES:
            continue
        relative = Path(*PurePosixPath(name).parts[1:]).with_suffix(".ipynb")
        target = output / "notebooks/course" / relative
        provenance = {"archive": archive.relative_to(ROOT).as_posix(),
                      "archive_sha256": archive_hash, "member": name,
                      "member_sha256": converter.digest(raw),
                      "aliases": [{"archive": jobs.relative_to(ROOT).as_posix(),
                                   "archive_sha256": converter.digest(jobs.read_bytes()),
                                   "member": an, "member_sha256": converter.digest(ar)}
                                  for an, ar, ad in aliases
                                  if [c.get("command") for c in ad["commands"]] ==
                                     [c.get("command") for c in doc["commands"]]
                                  and [c.get("results") for c in ad["commands"]] ==
                                      [c.get("results") for c in doc["commands"]]]}
        payload = output / "artifacts/notebook-payloads" / relative.with_suffix(".json")
        content = converter.pretty(converter.payload_document(raw, provenance)) + "\n"
        ref = Path(os.path.relpath(payload, target.parent)).as_posix()
        nb = converter.convert(doc, provenance, ref)
        nb["metadata"]["archived_databricks"]["payload_sha256"] = converter.digest(content.encode())
        preflight.append((target, [converter.convert(doc, provenance), nb]))
        manifest.append(dict(provenance, output=target.relative_to(output).as_posix(),
                             command_count=len(doc["commands"]), cell_count=len(nb["cells"]),
                             output_count=sum(len(c.get("outputs", [])) for c in nb["cells"])))
        nb, report = enricher.enrich(nb, target, ROOT, catalog)
        report["path"] = target.relative_to(output).as_posix()
        reports.append(report)
        plan.extend([(payload, content), (target, converter.pretty(nb) + "\n")])
    for asset in source_map["assets"]:
        if "study_copy" not in asset:
            continue
        source = ROOT / asset["new"]
        raw = source.read_bytes()
        target = output / asset["study_copy"]
        provenance = {"member": source.name, "original": asset["new"],
                      "member_sha256": converter.digest(raw)}
        payload = output / "artifacts/notebook-payloads/standalone" / source.with_suffix(".json").name
        content = converter.pretty(converter.payload_document(raw, provenance)) + "\n"
        nb = converter.compact_standalone(raw, provenance,
                     Path(os.path.relpath(payload, target.parent)).as_posix())
        nb["metadata"]["archived_standalone"]["payload_sha256"] = converter.digest(content.encode())
        preflight.append((target, [json.loads(raw), nb]))
        nb, report = enricher.enrich(nb, target, ROOT, catalog)
        report["path"] = target.relative_to(output).as_posix()
        reports.append(report)
        plan.extend([(payload, content), (target, converter.pretty(nb) + "\n")])
    for target, content in plan:
        if target.suffix == ".ipynb":
            errors = validator.notebook_errors(json.loads(content))
            if errors:
                raise ValueError(f"Invalid staged notebook shape ({target.name}): {sorted(set(errors))}")
    report_path = output / "artifacts/metadata/enrichment-report.json"
    plan.append((report_path, converter.pretty({"version": enricher.VERSION, "notebooks": reports}) + "\n"))
    plan.append((output / "artifacts/metadata/conversion-manifest.json",
                 converter.pretty({"notebooks": manifest}) + "\n"))
    if install:
        if len(preflight) != 71:
            raise ValueError("Canonical installation requires exactly 71 notebooks")
        # Entire repository preflight completes before the first file is written.
        for target, baselines in preflight:
            preflight_existing(target, baselines)
    stale = [p for p, content in plan if not p.exists() or p.read_text() != content]
    if not check:
        for path, content in plan:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"{len(reports)} staged notebooks; {len(stale)} {'stale' if check else 'updated'} files; no code executed.")
    return int(check and bool(stale))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".work/clean-samples")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install", action="store_true",
                        help="Explicitly refresh canonical copies after full learner-edit preflight")
    args = parser.parse_args()
    return generate(args.output, not args.all, args.check, args.install)


if __name__ == "__main__":
    raise SystemExit(main())
