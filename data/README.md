# Example data

Dataset families retain their original internal paths:

See the [human-readable catalog](catalog.md) and [machine-readable catalog](catalog.json)
for per-file hashes, schema hints, record counts, known defects, and lesson matches.

- `circuitbox/`: addresses, customers, and orders in daily batches.
- `gizmobox/`: monthly addresses, customers, orders, payments, membership images,
  and refunds seed SQL.
- `stock_prices/`: daily JSON inputs.
- `top_tech_companies/`: CSV inputs.

These are supplied learning examples, not production data. Preserve intentional
ingestion lanes and malformed records: they may illustrate schema handling or
data-quality behavior. Cataloging must report defects rather than silently clean
them. Archived notebook outputs are not substitutes for the original inputs.
