# Ordinary local prototype

Run `python3 probe.py` here with Python 3.11. The ordinary public region service durably publishes a one-rectangle snapshot and serves point classification without any track. The actual SQLite warehouse accepts ordinary points and persists queried facts, using the intentionally incomplete endpoint-inside approach.

The probe demonstrates ordinary success, the two-outside-endpoint failure, unsupported exclusion geometry, and a real catalog A→B product consumed by the warehouse. To isolate consumption, the latter uses a test-only exact single-rectangle clipping kernel; it does not implement unions, holes, revision processing, atomic batches, UNKNOWN, normalization, plan CLI or a complete solution. Its frozen-product control changes only consumed cells after actual B publication, retaining B identity and independent expected result.

All SQLite work is real and runs in temporary databases; the output includes rows reread from storage and snapshots obtained after normal reopen. No external data or network is required. The example demonstrates only the limited cases listed above.
