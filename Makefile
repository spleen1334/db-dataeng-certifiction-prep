PYTHON ?= python3

.PHONY: help inventory convert-sample convert catalog catalog-check test
help:
	@printf '%s\n' 'make inventory      Verify original asset checksums' 'make convert-sample Create three sample notebooks in .work/ (once)' 'make convert        Create course notebooks (once; refuses overwrites)' 'make catalog        Regenerate the dataset catalog' 'make catalog-check  Verify catalog freshness' 'make test           Run maintenance unit tests'

inventory:
	$(PYTHON) scripts/maintenance/inventory.py

convert-sample:
	$(PYTHON) scripts/maintenance/convert_dbc.py --sample --output .work/sample-notebooks --manifest .work/sample-conversion.json

convert:
	$(PYTHON) scripts/maintenance/convert_dbc.py --manifest docs/conversion-manifest.json

catalog:
	$(PYTHON) scripts/maintenance/catalog_data.py

catalog-check:
	$(PYTHON) scripts/maintenance/catalog_data.py --check

test:
	$(PYTHON) -m unittest discover -s scripts/maintenance -p 'test_*.py' -v
