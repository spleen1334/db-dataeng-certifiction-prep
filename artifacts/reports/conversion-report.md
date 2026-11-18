# Conversion and learning-material report

## Scope

- 69 main-archive notebooks converted: 27 Python and 42 SQL.
- 690 original commands retained in numeric Databricks display order.
- Three separate Jobs archive entries indexed as aliases to matching main-course
  notebooks; both original archives remain available.
- Two standalone notebooks retained, with separate immutable originals.
- 71 canonical study notebooks in total; temporary samples live only in `.work/`.
- 86 supplied dataset-family files cataloged without cleaning or changing bytes.

## Representation

Python source remains in code cells. SQL and unsupported Databricks magics are
labelled fenced source in Markdown, so a Python kernel cannot accidentally treat
them as Python. Output-only code cells carry historical results for those sources.
Original commands, results, errors, array indices, GUIDs, and display positions
are retained in cell metadata.

The original archive has 373 non-null result containers:

- 212 top-level tables, 159 result lists, one HTML and one HTML-sandbox result.
- Nested lists contain 90 tables, 21 MIME bundles, and eight ANSI outputs.
- Empty results are retained explicitly; three historical errors remain visible.

Tables are rendered as readable text with schema-derived column headings.
Available HTML/MIME output is retained, not re-created. Unsupported payloads
have a visible JSON fallback as well as exact archived metadata. No code was run
to produce new course outputs.

## Added learning material

Educational annotations and supplied input snapshots are marked
`learning_enriched`, separate from original cells. Input snapshots contain
complete supplied file contents or PNG attachments, with paths and hashes.
They are **inputs**, not executed results. Matching uses source references and
catalog evidence; a related input snapshot does not recreate an intermediate
Delta table, external database, catalog, or checkpoint.

The per-notebook additions are recorded in [enrichment-report.json](../metadata/enrichment-report.json).
Regeneration cannot overwrite enriched notebooks through the converter, even
with its overwrite flag. The enrichment command itself is deterministic and
replaces only its own labelled cells.

## Exceptions

- Nine original DLT image references cannot be resolved from supplied assets.
- Cloud-only input, intermediate state, and absent generated output remain
  unavailable. No data was fabricated or downloaded.
- Known malformed records, SQL defects, historic errors, and configuration issues
  are retained with separate corrective commentary.
- A topic-level exam map is deliberately marked partial; these materials do not
  establish readiness or complete coverage of every May 2026 objective.
- Original credentials remain in local source assets and faithful exports.
  Publication is blocked pending a separate sanitization policy.

See [known limitations](../../docs/known-limitations.md) for details,
[source-map.json](../metadata/source-map.json) for relocation provenance,
[conversion-manifest.json](../metadata/conversion-manifest.json) for archive-member
mappings, and [validation-report.json](../metadata/validation-report.json) for final machine checks.
