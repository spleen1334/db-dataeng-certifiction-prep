# Certification and AI preparation references

These notes summarize the supplied PDFs, not a live verification of the latest
exam or product behavior. Page numbers refer to PDF pages.

## Source roles

- The root course V7 PDF contains lecture slides and supplies the teaching sequence.
- [Exam guide](originals/certification_guide/databricks-certified-data-engineer-associate-exam-guide-may-2026-000.pdf):
  official scope for the exam version **as of May 4, 2026** (page 1).
- [AI Prep Guide](originals/certification_guide/ai-prep-guide-any-databricks-certification.pdf):
  a method for using AI to study for **any Databricks certification**, not a separate
  AI certification or a collection of AI engineering notebooks (page 1).

## Exam scope

| Domain | Weight | Exam guide pages |
| --- | ---: | --- |
| Databricks Intelligence Platform | 6% | 2 |
| Data Ingestion and Loading | 21% | 2 |
| Data Transformation and Modeling | 22% | 2–3 |
| Working with Lakeflow Jobs | 16% | 3 |
| Implementing CI/CD | 10% | 3 |
| Troubleshooting, Monitoring, and Optimization | 10% | 3–4 |
| Governance and Security | 15% | 4 |

The guide specifies 45 scored multiple-choice questions, 90 minutes, and no test
aides. Unidentified unscored questions may appear, with additional time allowed.
There are no required prerequisites; training and six months of hands-on
experience are recommended (page 1).

### How to use this in the repository

Map each objective to actual notebook cells, queries, datasets, and slide pages.
Use **unknown**, **partial**, or **demonstrated** coverage rather than assuming a
filename proves coverage. Demonstrated coverage means supporting learning material
was inspected, not that the learner has mastered it.

Ingestion and transformation together account for 43%. Their examples are a useful
starting point, but review Jobs, CI/CD, operations, and governance explicitly.
Potential gaps must remain visible instead of being filled with invented lessons.

### Version cautions

- The sample questions are explicitly retired from a previous exam version
  (page 4); they do not guarantee current coverage.
- Page 3 uses Git Folders (formerly Repos) and more than one bundle name.
  Preserve source wording and verify current terminology separately.
- The retired sample on page 6 uses “high-concurrency cluster.” Do not present
  that wording as independently verified current compute guidance.
- Page 4 mentions `DENY` and managed/external table conversion. Verify supported
  behavior in official product documentation before adding explanatory code.
- Recheck the live official guide two weeks before the exam
  (AI Prep Guide, page 1). The supplied PDF is a versioned baseline only.

## What the AI guide contributes

The guide recommends:

1. Supply the exam guide every study session; require official Databricks
   documentation or Academy sources and explicit uncertainty when verification
   is unavailable (pages 1–2).
2. Keep a verified table of renamed products and unfamiliar terms (page 2).
3. Follow **orient → diagnose → deep dive → practice → repair**, withholding
   quiz answers until the learner responds (pages 2–3).
4. Design 6–10 small, objective-mapped hands-on tasks and perform them in a
   Databricks workspace (page 3).
5. Use diagnosis first, weak-objective study and labs next, and mocks last
   (page 3).

AI-generated mocks are **not calibrated readiness checks** (page 3). Resolve
conflicting AI answers with official documentation, not a majority vote. A
provided citation should itself be checked for relevance and support.

## Deferred learning additions

**Not started; separate explicit approval required.** These activities are tracked
only in [AI-PREPARATION-TODO.md](AI-PREPARATION-TODO.md), after all other work.

- A Markdown study journal for weak objectives, misconceptions, unfamiliar terms,
  verified terminology, source URLs, and verification dates.
- A reusable AI tutor prompt constrained to the exam objectives.
- Objective-mapped diagnostics and clearly labelled AI-generated practice questions.
- Optional small labs, only after workspace permissions, feature availability,
  and cost have been checked.

These are Stage 2 candidates, not requirements to run Spark locally. A readable
repository is useful study material but is not a substitute for the practical
experience recommended by the guides.
