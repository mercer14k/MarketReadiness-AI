# Benchmark suite

The executable harness is `packages/marketreadiness/evaluation/benchmark.py`.

Run `python -m marketreadiness.evaluation.benchmark --scale 10 --repeats 5` from the project root. Larger datasets are generated deterministically in memory; file generation is available through `python -m marketreadiness.data.generator`.

Timing and memory passes are separate. No arbitrary wall-clock threshold is used as a flaky CI assertion. CI asserts domain/evaluation invariants and uploads the measured JSON/CSV/Markdown for inspection. See `docs/evaluation.md` for scope and limitations.
