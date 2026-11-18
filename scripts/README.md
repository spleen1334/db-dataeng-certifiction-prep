# Scripts and queries

- `maintenance/`: repository inventory, conversion, cataloging, and validation.
- `examples/`: original standalone Python examples; execution may contact Databricks.
- `sql/`: original standalone SQL/DDL examples.

Use the root Makefile for maintenance commands. Maintenance does not execute the
course, connect to Spark, or deploy resources.

Requirements: Python 3.10+ and Make. The maintenance scripts use only the Python
standard library; if `nbformat` is already installed, validation also uses its
schema checks. No dependency installation is required.

Start with `make help`. `make verify` is read-only apart from ordinary Python
bytecode caches (ignored by Git). `make catalog`, `make index`, and `make enrich`
regenerate derived material. Conversion commands are one-time creation operations
and refuse overwriting existing notebooks; enriched notebooks remain protected
even if the converter is invoked directly with `--overwrite`.

Sample notebooks live in ignored `.work/`. They are not additional canonical
lessons. Maintenance does not provide a “clean” operation that could delete
original learning assets.
