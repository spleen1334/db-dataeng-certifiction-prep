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
Array indices, GUIDs, and display positions remain in lightweight cell metadata.
Complete original documents, commands, results, and errors are preserved in
external payloads under `artifacts/notebook-payloads/`, referenced by path and
SHA-256 from each reading notebook. Exact original bytes are preserved too.

The original archive has 373 non-null result containers:

- 212 top-level tables, 159 result lists, one HTML and one HTML-sandbox result.
- Nested lists contain 90 tables, 21 MIME bundles, and eight ANSI outputs.
- Empty results are retained explicitly; three historical errors remain visible.

Tables use static escaped HTML with plain-text alternatives, showing at most
10 saved rows and 200 characters per value. All columns remain represented.
Nested/binary values are labelled as omitted; unknown rich payloads are summarized
rather than dumped as JSON. Complete values remain in the linked external payload.
Safe saved HTML tables are reconstructed from cell text, without original scripts,
styles, or event handlers. No code was run to produce new course outputs.

## Added learning material

Educational annotations are marked `learning_enriched`, separate from original
source cells. Complete supplied text/image inputs stay in `data/`, rather than
being embedded repeatedly before the lesson. Short dataset references link to
them. Only selective complex-operation explanations are added.
Matching uses source references and catalog evidence; related companies files
are explicitly not verified copies of remote state. Local inputs do not recreate
an intermediate Delta table, database, catalog, or checkpoint.

The per-notebook additions are recorded in [enrichment-report.json](../metadata/enrichment-report.json).
Regeneration cannot overwrite enriched notebooks through the converter, even
with its overwrite flag. A guarded refresh checks original cells against the
archives before replacing generated study copies; learner source/output changes
must not be silently overwritten. The enrichment command replaces only its own
labelled cells.

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
- Static Chromium rendering was checked. Actual VS Code/Jupyter application
  rendering was not tested; Jupyter was unavailable and no packages were installed.

See [known limitations](../../docs/known-limitations.md) for details,
[source-map.json](../metadata/source-map.json) for relocation provenance,
[conversion-manifest.json](../metadata/conversion-manifest.json) for archive-member
mappings, and [validation-report.json](../metadata/validation-report.json) for final machine checks.
