# Reading archived notebooks

The study notebooks are for reading original lesson code alongside saved results,
without starting Spark or contacting Databricks. A saved result is a historical
observation, not evidence of a current execution.

## Presentation policy

- Start with a short lesson objective, then show source and its saved result.
- Display tabular results as static HTML tables with a plain-text fallback.
- Clearly label bounded previews and shortened values. A saved row count is not
  necessarily the total number of rows in the original source table.
- Keep complete inputs in `data/` and original materials in `materials/`.
  Do not repeat whole JSON files or image collections before the lesson.
- Group input references by dataset folder with a file count; do not replace
  50 embedded images with another 50-link preamble.
- Preserve full archived payloads outside the reading notebooks, with provenance
  references rather than duplicate result JSON in cell metadata.
- Retain explanations that teach a particular operation; avoid repeating generic
  advice before every SELECT or display command.
- Illustrative examples are unexecuted teaching material, not generated results.

## Compatibility and safety

The portable target is the standard Jupyter notebook format: static
`text/html` with useful `text/plain` alternatives, no JavaScript, widgets, custom
renderer extensions, or forced notebook trust. Data-derived HTML must be escaped.
Viewer trust and sanitization rules may affect styling and rich output.

These notebooks are not a Databricks grid: interactive sorting, filtering, and
identical appearance across viewers are not promised. Code still depends on its
original runtime and services if executed.

Full local archives may contain credentials and author-specific information.
Moving payloads out of the reading flow does not sanitize them for publication.

## Maintenance and verification

Changes to presentation must preserve original source, row order, column names,
and complete underlying payloads. Test preview limits and HTML escaping, verify
external payload hashes against the original materials, and compare samples
before regenerating the whole collection.

When a viewer or optional package is unavailable in the verification environment,
record that limitation rather than describing structural or browser checks as
an actual VS Code/Jupyter application test.

### Preview limits

Tables show up to 10 archived rows, preserving all columns. Individual values are
limited to 200 characters; nested/binary values receive explicit omission labels.
The renderer shows up to 20 result outputs, followed by summaries of omitted or
empty results. Full values remain available in the referenced archive payload.
Original active HTML is not executed to reproduce a historical display.
Saved HTML tables can be rebuilt from their cell text only, discarding original
scripts, styling, and attributes.

### Rendering checks

A synthetic static Chromium check confirmed all 17 columns remained present in
a wide table, 10 of 13 saved rows were shown, horizontal scrolling worked, and
null/truncated/nested/binary markers were visible. The generated output contained
no scripts or HTML event attributes.

This is **not** an application-level VS Code or Jupyter Notebook test. Jupyter
is not installed in the verification environment; no dependencies were installed
to claim otherwise. Both viewers support standard saved notebook MIME outputs,
but their trust policies and rendering can differ.
