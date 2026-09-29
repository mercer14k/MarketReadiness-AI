# ADR 0001: Deterministic planning owns operational state

Status: accepted.

Coverage scores, constraints, inventory balances, phase paths and transfers must be reproducible and auditable. A finite-supply allocation engine operates on immutable validated snapshots. All calculations happen before any LLM call. The optional model selects evidence IDs; approved text is rendered by code.

Consequence: strong numerical and grounding invariants, with intentionally limited prose flexibility. The product remains useful offline with no model installed. A future assistant can explain domain rules but must not become the state authority.
