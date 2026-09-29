"""Capture exact installed dependency versions without machine-specific editable paths."""

from importlib.metadata import distribution, distributions
from pathlib import Path

from packaging.requirements import Requirement

RUNTIME = ["fastapi", "uvicorn", "pydantic", "sqlalchemy", "psycopg[binary]", "httpx", "polars"]
resolved = {}


def visit(spec):
    req = Requirement(spec)
    dist = distribution(req.name)
    name = dist.metadata["Name"]
    if name.lower() in resolved:
        return
    resolved[name.lower()] = f"{name}=={dist.version}"
    for dep in dist.requires or []:
        r = Requirement(dep)
        extras = req.extras or {""}
        if not r.marker or any(r.marker.evaluate({"extra": extra}) for extra in extras):
            visit(str(r))


for spec in RUNTIME:
    visit(spec)
Path("requirements.txt").write_text(
    "# Exact runtime dependency lock; Python 3.12+\n"
    + "\n".join(sorted(resolved.values(), key=str.lower))
    + "\n"
)
lines = [
    f"{d.metadata['Name']}=={d.version}"
    for d in distributions()
    if d.metadata["Name"].lower() not in {"market-readiness-ai", "pip", "setuptools"}
]
Path("requirements-dev.txt").write_text(
    "# Exact development and test dependency lock\n"
    + "\n".join(sorted(lines, key=str.lower))
    + "\n"
)
