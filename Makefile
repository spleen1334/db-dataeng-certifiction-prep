PYTHON ?= python3

.PHONY: help inventory
help:
	@printf '%s\n' 'make inventory  Verify relocated original assets against their checksums' 'Additional extraction/catalog/validation targets are added with their implementation stages.'

inventory:
	$(PYTHON) scripts/maintenance/inventory.py
