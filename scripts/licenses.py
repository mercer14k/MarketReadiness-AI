"""Generate an auditable inventory from installed Python and pnpm package metadata."""

import json
from importlib.metadata import distributions
from pathlib import Path

root = Path(__file__).resolve().parents[1]
python = []
for dist in distributions():
    name = dist.metadata["Name"]
    if name.lower() in {"pip", "market-readiness-ai"}:
        continue
    license = (
        dist.metadata.get("License-Expression")
        or dist.metadata.get("License")
        or "See upstream metadata"
    )
    classifiers = [c for c in dist.metadata.get_all("Classifier", []) if c.startswith("License ::")]
    python.append(
        {
            "name": name,
            "version": dist.version,
            "license": license[:300],
            "license_classifiers": classifiers,
            "project_urls": dist.metadata.get_all("Project-URL", []),
        }
    )
web = []
for package in (root / "apps/web/node_modules/.pnpm").glob("*/node_modules/*/package.json"):
    raw = json.loads(package.read_text())
    web.append(
        {
            "name": raw["name"],
            "version": raw["version"],
            "license": raw.get("license", "See upstream LICENSE"),
            "repository": raw.get("repository"),
        }
    )
for package in (root / "apps/web/node_modules/.pnpm").glob("*/node_modules/@*/*/package.json"):
    raw = json.loads(package.read_text())
    web.append(
        {
            "name": raw["name"],
            "version": raw["version"],
            "license": raw.get("license", "See upstream LICENSE"),
            "repository": raw.get("repository"),
        }
    )
web = list({(p["name"], p["version"]): p for p in web}.values())
(root / "docs/dependency-inventory.json").write_text(
    json.dumps(
        {
            "note": "Declared installed-package metadata. Runtime and development dependencies included; OS image packages are separately licensed.",
            "python": sorted(python, key=lambda p: p["name"].lower()),
            "javascript": sorted(web, key=lambda p: p["name"].lower()),
        },
        indent=2,
    )
    + "\n"
)
