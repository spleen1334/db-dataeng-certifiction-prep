# Local maintenance artifacts

`metadata/` holds generated manifests, enrichment and validation evidence, and the
source map recording preserved asset paths and SHA-256 checksums. `reports/`
holds maintenance reports. These local artifacts are separate from the
human learning documentation in `docs/`; they do not represent new course execution.

`notebook-payloads/` preserves complete original notebook documents and exact source
bytes, including full historical results and errors. Reading notebooks link to
these payloads with SHA-256 references instead of embedding duplicate JSON.
These files may contain original credentials: they are local archival material,
not sanitized publication artifacts.
