PYTHON ?= python3

.PHONY: help inventory convert-sample convert clean-samples clean-samples-check refresh-notebooks catalog catalog-check index index-check enrich enrich-check validate verify test
help:
	@printf '%s\n' 'make inventory      Verify original asset checksums' 'make convert-sample Create compact samples in .work/ (once)' 'make convert        Create compact course notebooks (once; refuses overwrites)' 'make refresh-notebooks Explicit guarded canonical refresh; refuses learner edits' 'make catalog        Regenerate the dataset catalog' 'make catalog-check  Verify catalog freshness' 'make index          Regenerate notebook navigation' 'make index-check    Verify notebook navigation freshness' 'make enrich         Add concise learning notes and original-input links' 'make enrich-check   Verify enrichment freshness without writing' 'make validate       Check notebook fidelity, original hashes, catalog and links' 'make verify         Run unit tests and all read-only checks' 'make test           Run maintenance unit tests'

inventory:
	$(PYTHON) scripts/maintenance/inventory.py

convert-sample:
	$(PYTHON) scripts/maintenance/convert_dbc.py --compact --sample --output .work/sample-notebooks --payload-dir .work/artifacts/notebook-payloads --manifest .work/sample-conversion.json

convert:
	$(PYTHON) scripts/maintenance/convert_dbc.py --compact --payload-dir artifacts/notebook-payloads --manifest artifacts/metadata/conversion-manifest.json

refresh-notebooks:
	$(PYTHON) scripts/maintenance/clean_notebooks.py --install

clean-samples:
	$(PYTHON) scripts/maintenance/clean_notebooks.py

clean-samples-check:
	$(PYTHON) scripts/maintenance/clean_notebooks.py --check

catalog:
	$(PYTHON) scripts/maintenance/catalog_data.py

catalog-check:
	$(PYTHON) scripts/maintenance/catalog_data.py --check

test:
	$(PYTHON) -m unittest discover -s scripts/maintenance -p 'test_*.py' -v

index:
	$(PYTHON) scripts/maintenance/index_notebooks.py

index-check:
	$(PYTHON) scripts/maintenance/index_notebooks.py --check

enrich:
	$(PYTHON) scripts/maintenance/enrich_notebooks.py --output artifacts/metadata/enrichment-report.json

enrich-check:
	$(PYTHON) scripts/maintenance/enrich_notebooks.py --check

validate:
	$(PYTHON) scripts/maintenance/validate_repository.py

verify: test index-check enrich-check validate
