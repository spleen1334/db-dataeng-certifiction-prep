# Exam coverage cross-reference

Baseline: [supplied exam guide](../originals/certification_guide/databricks-certified-data-engineer-associate-exam-guide-may-2026-000.pdf),
version as of May 4, 2026, pages 2–4. This is a **partial topic-level map**,
not proof of complete objective coverage or learner readiness.

| Domain | Weight | Slide pages | Supporting examples | Coverage / verification needs |
| --- | ---: | --- | --- | --- |
| Platform | 6% | 52–94, 201–223 | Platform and Delta notebooks | Partial: inspect compute limitations/cost trade-offs |
| Ingestion/loading | 21% | 118–223 | ETL, streaming, Auto Loader, JDBC | Partial: connector breadth, REST/ODBC, selection trade-offs need verification |
| Transformation/modeling | 22% | 118–165, 237–304 | SQL/PySpark transformations and pipelines | Partial: broad DataFrame operations, tuning parameters, gold object distinctions |
| Lakeflow Jobs | 16% | 225–236 | Three bronze/silver/gold notebooks | Partial: configuration/control flow and trigger coverage not established by SQL alone |
| CI/CD | 10% | 91–94, 406–414 | Git demo and standalone bundle | Partial: variables/overrides, CLI, deployment/promotion; supplied bundle path is broken |
| Troubleshooting/optimization | 10% | 346–380 | Delta maintenance examples | Partial: run history, Spark UI diagnosis, startup/library/OOM troubleshooting |
| Governance/security | 15% | 95–117, 308–345 | Unity Catalog and security notebooks | Partial: verify individual operations and access-control semantics |

The archive's Databricks SQL folder has no notebooks. Missing notebook support
does not necessarily mean the corresponding slide topic is absent.

## Verification backlog, not invented coverage

- Match each official objective to exact notebook cells and slide pages during
  personal study; mark unsupported objectives explicitly.
- Verify current names and behaviors in official Databricks documentation before
  relying on historical examples.
- In particular, confirm the guide's `DENY` wording and managed/external table
  conversion semantics; these notes do not assert supported implementations.
- Treat retired sample questions as historical examples, not current readiness tests.
- Recheck the live guide two weeks before the exam.

AI-assisted preparation remains separately approval-gated and is not part of
this work.
