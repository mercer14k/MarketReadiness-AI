"""Create a source-only archive, excluding secrets, installed packages and runtime state."""

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

EXCLUDED = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "test-results",
    "playwright-report",
    "artifacts",
    "htmlcov",
    "generated",
}


def source_files(root):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if not path.is_file() or any(
            p in EXCLUDED or p.endswith(".egg-info") for p in relative.parts
        ):
            continue
        if (
            path.name in {".DS_Store", ".coverage", "tsconfig.tsbuildinfo"}
            or path.suffix in {".pyc", ".db", ".zip"}
            or ".db-" in path.name
        ):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/market-readiness-ai-source.zip")
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        for path in source_files(root):
            archive.write(path, Path("market-readiness-ai") / path.relative_to(root))
    print(args.output.resolve())


if __name__ == "__main__":
    main()
