# Known limitations and original example defects

## Availability and fidelity

- The primary archive contains 69 notebooks and 690 commands. The three notebooks
  in the separate Jobs archive duplicate source/results in the main archive.
- Stored command arrays are not display order in 66 notebooks; conversion must
  sort numeric `position` while preserving provenance.
- The archive contains 373 non-null result containers, including nested outputs,
  empty results, and three historical errors. This is not 373 complete datasets.
- Nine DLT Markdown image references have no corresponding archived image files.
- Cloud tables, JDBC state, checkpoints, and absent outputs cannot be reconstructed.
- Lecture slides are V7, archive V5; exam scope is the supplied May 2026 baseline.

## Data and example issues retained unchanged

| Source | Issue | Learning interpretation |
| --- | --- | --- |
| `data/gizmobox/orders/orders_2024_10.json:9` | Malformed JSON | Inspect corrupt-record handling |
| November orders `:11`, December `:21`, January `:2,:8` | Four additional malformed JSON lines | Do not silently remove training records |
| `data/gizmobox/payments/*.csv` | Headerless files | SQL extraction uses `header=true`, which can discard a first record; Python counterpart omits it |
| `scripts/sql/refunds_azure_sql_ddl.sql:6` and dataset copy | `NOT NULL.` punctuation | Remove the period in a separate corrected copy; this is the final column, so no trailing comma is needed |
| Three customer ingestion directories | Identical monthly contents | Intentional separate ingestion lanes |
| `config/bundle-demo/databricks.yml:12` | Referenced notebook path already absent | Configuration is a historical example, not deployment-ready |
| Standalone companies report | Input is an external table | Saved aggregate does not include the complete source table |

## Safety

Embedded JDBC credentials and author-specific workspace information exist in the
original materials. Validity is unknown. Preserve locally for provenance; do not
publish archives, exports, or Git history without an agreed sanitization review.
No credentials are reproduced in these notes.

Original code and saved outputs are not silently corrected. Added commentary is
separate and should not be mistaken for a new execution result.
