# Learning repository TODO

This repository is for studying Databricks data engineering. The course PDF
contains lecture slides; the notebooks, queries, and datasets are supporting
examples. Local Spark execution is not a goal.

## Safety checkpoint

- [x] Initialize local Git and commit the original materials with a `.gitignore`.
- [x] Leave the repository local only, with no remote configured.
- [ ] Review hard-coded JDBC credentials found inside the original DBC archive.
  Their validity is unknown. Do not reproduce their values in documentation.
  Keep this snapshot local; agree a sanitization policy covering archives,
  converted notebooks, and Git history before any future sharing.
- [ ] Review author-specific workspace URLs in the bundle configuration before sharing.
- [x] Approve the revised organization and extraction plan before moving files.

## Planning reviews

- [x] Oracle: investigate the certification exam guide, citing PDF pages for
  exam objectives and preparation priorities.
- [x] Separate Oracle review: investigate the AI Prep Guide alongside the exam
  guide; identify useful AI-assisted study practices and possible later exercises.
- [x] Oracle: investigate the main course assets and prepare the extraction,
  organization, and validation plan.
- [x] Reconcile these findings into a concrete plan and this checklist.

Guide review findings are recorded in [docs/guide-findings.md](docs/guide-findings.md).
The AI guide describes AI-assisted preparation, not a separate AI certification.
The revised plan was approved. Work proceeds in verified, committed stages.
AI-assisted preparation is excluded from execution and requires separate approval.

### Confirmed extraction constraints

- Main archive: 69 notebooks and 690 commands. The three separate Jobs notebooks
  duplicate main-archive source/results; index them as aliases rather than making
  duplicate study copies. Including the two existing standalone notebooks gives
  71 canonical notebooks.
- Sort commands by numeric `position`: 66 of 69 stored arrays are not in display
  order. Retain original array indices and command identifiers for provenance.
- Preserve 373 non-null saved-result containers, including nested outputs and
  three historical errors. A container is not necessarily a complete dataset.
- Nine DLT image references point to missing assets; report rather than fabricate.
- Preserve known example defects: five malformed orders JSON lines, a SQL
  header-setting mismatch for headerless payments, and the refunds DDL typo.
  Add corrective explanations only as separately labelled learning material.
- Preserve all three customer ingestion directories despite identical contents.
- Document the bundle configuration's already-missing notebook path; do not claim
  the example is deployment-ready after relocation.

Parent spot-check validation exited 0 for archive coverage, Jobs duplication,
display ordering, nested output counts, historical errors, malformed orders, and
duplicate refunds SQL. No notebook execution was performed.

## Stage 1 — Structure and readable learning materials

- [ ] Organize datasets under `data/`, notebooks under `notebooks/`, scripts and
  SQL queries under `scripts/`, and reference material/documentation under `docs/`.
- [ ] Preserve original PDFs and DBC archives with source mappings and checksums.
- [ ] Check path dependencies before relocating standalone examples/configuration.
- [ ] Add root and directory README files with a clear study path.
- [ ] Catalog datasets, formats, relationships, provenance, and relevant lessons.
- [ ] Expose maintenance and validation activities as Makefile targets; keep
  implementation scripts in `scripts/`.
- [ ] Convert representative DBC notebooks first, then validate before bulk conversion.
- [ ] Preserve source cells and all available archived results in readable notebooks.
  Explicitly identify missing, truncated, or externally stored results.
- [ ] Determine which supplied input data can usefully be embedded for reading.
  Do not invent missing data or claim that external cloud datasets are included.
- [ ] Write page-referenced Markdown learning notes from the lecture slides and
  guides, distinguishing source content from added explanations.
- [ ] Document differences between the V7 slides, V5 archive, and exam guide.
- [ ] Map inspected material to the seven May 2026 exam domains; explicitly mark
  unknown/partial coverage and documentation-verification items.
- [ ] Validate archive coverage, notebook format, source/output preservation,
  internal links, dataset catalog, and unchanged original content.

## Stage 2 — Educational enrichment

- [ ] Review every notebook for learning clarity.
- [ ] Add clearly identified explanatory Markdown and code comments without
  changing the original course behavior.
- [ ] Explain difficult concepts with small, clearly labelled teaching examples.
- [x] Defer all AI-assisted preparation to
  [docs/AI-PREPARATION-TODO.md](docs/AI-PREPARATION-TODO.md); do not initiate it.
- [ ] Recheck the official exam guide two weeks before the learner's exam.

## Boundaries

- No remote repository or uploads.
- No local Spark setup or cloud workload execution.
- No fabricated saved outputs or claims of full embedded data when sources are absent.
- AI-assisted preparation remains blocked until separate explicit approval.
