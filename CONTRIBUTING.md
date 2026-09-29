# Contributing

The most valuable contribution is a reproducible supply-chain failure case with a clear expected outcome.

1. Read the planning semantics in `docs/architecture.md` and choose one bounded problem.
2. Add a deterministic fixture and a test that fails for the current behavior.
3. Keep numerical logic in `packages/marketreadiness/domain`, orchestration in services, and presentation in the web app.
4. Preserve source IDs, validation visibility, deterministic operation without an LLM, and immutable scenario semantics.
5. Run backend checks, frontend checks and relevant browser workflows using `docs/development.md`.
6. Explain the trigger, before/after behavior, test evidence and limitations in the pull request. Attach measured results for performance claims.

Never include credentials or real customer data. New dependencies need a documented license and a clear purpose. Model adapters must remain local, follow `LocalRuntime`, preserve schema/evidence validation, and be benchmarked without changing domain logic. New numerical algorithms require an ADR, fixed-seed tests and a version bump.

Use small, reviewable changes. Practitioners are welcome to contribute terminology, units, guardrail policy, counterexamples and sanitized synthetic cases. Security reports follow SECURITY.md. Contributions are submitted under the repository's Apache-2.0 license.
