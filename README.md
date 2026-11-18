# Databricks certification learning repository

Read the lecture slides alongside archived notebooks, example queries, and
supplied datasets. **No local Spark installation is required for reading.**
Examples may require Databricks and external services to execute.

## Start here

1. Read the [documentation index](docs/README.md).
2. Follow the course's original section and lesson order in
   [notebooks](notebooks/README.md).
3. Inspect [example data](data/README.md) alongside the corresponding lessons.
4. Use the [certification reference](docs/guide-findings.md) to distinguish
   course coverage from the supplied exam objectives.

Notebooks show code with compact, prepopulated result previews. See the
[reading guide](docs/notebook-reading.md) for how complete data is preserved
outside the notebook body and what works without running a kernel.

## Layout

| Directory | Purpose |
| --- | --- |
| `data/` | Supplied training data, with original internal directory structure |
| `notebooks/` | Readable course notebooks and existing standalone examples |
| `scripts/` | Maintenance scripts, standalone Python examples, SQL queries |
| `config/` | Original Databricks bundle configuration |
| `docs/originals/` | Unmodified lecture slides and PDF guides |
| `docs/` | Human-readable learning notes, navigation, and limitations |
| `materials/` | Preserved DBC archives and original standalone notebooks |
| `artifacts/` | Local maintenance metadata and reports |

Maintenance activities are exposed through `make help`. Reading the files does
not execute them, contact cloud services, or deploy resources.

## Important limitations

- Saved outputs are historical, not fresh execution results. Missing cloud
  tables or generated state cannot be reconstructed from an archive.
- Original examples intentionally remain unchanged, including known defects.
  Added learning explanations are labelled separately.
- The slides are V7, the primary DBC archive is V5, and the supplied exam guide
  describes the version as of May 4, 2026. They are not interchangeable.
- **Local only:** original materials contain embedded JDBC credentials of unknown
  validity and author-specific workspace information. Do not share this repository
  without reviewing archives, readable exports, and Git history.
- Archived HTML/rich output is source material; inspect it in a trusted local
  environment. Do not execute notebooks or follow embedded external links blindly.

Progress is tracked in [TODO.md](TODO.md). AI-assisted preparation is **not
started** and requires separate explicit approval; see
[AI preparation backlog](docs/AI-PREPARATION-TODO.md).
