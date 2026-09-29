"""Offline structural checks. These do not substitute for starting Docker."""

import json
import re
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
assert set(compose["services"]) == {"api", "web", "db", "ollama"}
for service in compose["services"].values():
    if "build" in service:
        assert (ROOT / service["build"]["dockerfile"]).is_file()
    for port in service.get("ports", []):
        assert port.startswith("127.0.0.1:"), "Demo ports must bind to loopback"
workflow = yaml.safe_load((ROOT / ".github/workflows/ci.yml").read_text())
assert {"backend", "frontend", "compose-e2e", "dependency-audit"} <= workflow["jobs"].keys()
schema = json.loads((ROOT / "data/schemas/dataset.schema.json").read_text())
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(json.loads((ROOT / "data/sample/portfolio.json").read_text()))
missing = []
for markdown in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")]:
    for link in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", markdown.read_text()):
        target = link.split("#")[0]
        if not target or "://" in target or target.startswith("mailto:"):
            continue
        if not (markdown.parent / target).exists():
            missing.append(f"{markdown.name}: {target}")
assert not missing, missing
print("PASS: schemas, local documentation links, loopback defaults, Compose paths and CI structure")
print("Docker execution and hosted CI are separate release gates.")
