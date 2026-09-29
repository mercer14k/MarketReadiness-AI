# ADR 0003: Immutable aggregate snapshots in PostgreSQL; SQLite for native demo

Status: accepted.

Store schema-validated portfolio snapshots and scenarios as JSON documents, plus an active pointer and idempotency ledger in relational tables. This preserves an exact reproducible input for each calculation and enables one atomic import. PostgreSQL is the Compose default, with separate reader and writer identities. SQLite reduces native startup prerequisites and supports fast isolated tests.

Consequence: a clean audit boundary and no partial-import state, but the full snapshot is loaded into memory. Row-level analytical queries, incremental CDC and multi-cohort programs need normalized/event-based storage later. Initial schema uses SQLAlchemy `create_all`; a migration framework becomes necessary before changing deployed table structure. This is not claimed as an ERP connector or a warehouse-scale data platform.
