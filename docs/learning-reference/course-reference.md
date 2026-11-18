# Course learning reference

Use these notes beside the [V7 lecture slides](../originals/Databricks+Certified+Data+Engineer+Associate+Course+V7.pdf).
Numbers below are **PDF page numbers**, not printed slide numbers. These are added
study explanations, not verbatim slides or a guarantee of exam coverage.

## Reading sequence

| Pages | Topic | Notebook section |
| --- | --- | --- |
| 28–31, 34–51 | Roadmap, lakehouse, medallion | ETL, Delta, Jobs |
| 52–94 | Platform, compute, notebooks, Git | `dea01-databricks-lakehouse-platform` |
| 95–117 | Unity Catalog and cloud storage access | `dea02-unity-catalog` |
| 118–165 | SQL/PySpark ETL and DataFrames | `dea03-etl-with-apache-spark` |
| 166–181 | Structured Streaming | `dea03-etl-with-apache-spark-streaming` |
| 182–200 | Auto Loader and ingestion connectors | Streaming and ETL |
| 201–223 | Delta Lake | `dea04-delta-lake` |
| 225–236 | Lakeflow Jobs | `dea05-databricks-jobs` |
| 237–304 | Declarative pipelines, quality, SCD | `dea06-delta-live-tables` |
| 305–307 | Databricks SQL | No notebooks in supplied SQL section |
| 308–345 | Governance and security | Unity Catalog and `dea09-data-security` |
| 346–380 | Spark and Delta performance | Partial Delta maintenance examples |
| 381–405 | Sharing, federation, Databricks Connect | `dea08-delta-sharing-and-lakehouse-federation`; standalone report |
| 406–414 | Bundles and deployment | Standalone bundle demonstration |
| 415–421 | Course exam overview/practice | Compare with official exam guide |

## Concepts to track while reading

### Lakehouse and medallion — pages 34–51

A lakehouse brings transactional table and governance capabilities to data stored
in a lake. Medallion layers describe increasing refinement, not three mandatory
physical storage systems. Bronze retains ingested material; silver resolves
quality and integration concerns; gold presents business-oriented outputs.

In the companies Jobs example, follow which task produces each downstream input.
Ask what must be rerun if bronze changes, and whether a repeated run duplicates data.

### Platform and governance setup — pages 52–117

Compute executes work; storage retains data; governance determines authorized
access. Keep those responsibilities separate when reading paths and SQL objects.
A catalog/schema/table name is not the same thing as a cloud storage location.
Storage credentials and external locations connect governed access to external
storage; local copies of CSV files do not recreate those permissions.

### ETL and semi-structured data — pages 118–165

Distinguish a schema from actual rows. A field can be missing, null, incorrectly
typed, or nested; each requires a different treatment. Before joining, identify
the keys and expected cardinality: duplicate keys can multiply rows even when
the join expression is syntactically correct.

For aggregation, state the output grain in words first—for example “one row per
customer”—then check whether every grouping column belongs to that grain.
Supplied malformed orders records and headerless payments are important reading
examples; see [known limitations](../known-limitations.md).

### Streaming and ingestion — pages 166–200

Structured Streaming incrementally processes an unbounded input. A trigger
controls when processing runs; an output mode controls what changes are emitted.
A checkpoint records progress and recovery state; it is not a copy of all input
data. A notebook's saved table cannot reconstruct a streaming checkpoint.

Auto Loader addresses file discovery and schema handling. Keep schema inference,
schema evolution, and malformed-record handling conceptually separate. The
duplicate customer folders are different example ingestion lanes, not redundant
files to delete.

### Delta Lake — pages 201–223

Delta's transaction log records table state changes. Reading a current table,
viewing history, restoring a version, and removing obsolete files solve different
problems. Before reading a `MERGE`, identify its match key and what happens for
matched versus unmatched records. Before `VACUUM`, distinguish logical history
from whether historical data files remain available.

### Orchestration — pages 225–236

Jobs coordinate tasks and dependencies; they do not by themselves explain the
business transformation. Trace the bronze → silver → gold dependency graph, then
inspect each notebook's input/output contract. Retrying a task is safe only when
its side effects and write behavior support repetition.

### Declarative pipelines — pages 237–304

Read table declarations as a dependency graph. The framework manages execution,
while definitions describe the desired datasets. Expectations express quality
rules; inspect whether a failure is retained, dropped, or causes processing to
fail. SCD examples distinguish replacing current values from retaining changes
over time. Missing archived diagrams are reported, not reconstructed.

### SQL analytics and security — pages 305–345

A view is a query definition, not necessarily a separately stored result.
Access to a dataset and visibility of individual rows/columns are different
questions. When reading security examples, identify the principal, governed
object, privilege, and filtering/masking rule separately.

### Performance — pages 346–380

Begin with evidence: scanned data, partition sizes, shuffle, skew, and spill.
More compute does not automatically fix a single disproportionately large task.
File layout and query execution are related but distinct tuning concerns.
Saved outputs document a past run, not a current performance benchmark.

### Sharing and development — pages 381–414

Sharing, federation, and copying data are different access patterns.
Databricks Connect runs supported workloads against remote Databricks compute;
it does not turn this repository into a local Spark environment.
Bundle configuration describes deployable resources and environment targets,
but the supplied bundle has an already-missing notebook reference and should
not be treated as deployment-ready.

## Version boundaries

The slides are V7 and the notebooks V5. Preserve historical names in original
code and explain terminology separately. For exam alignment, use the supplied
May 2026 objective map rather than the course's older practice section.
No examples here have been executed or independently benchmarked.
