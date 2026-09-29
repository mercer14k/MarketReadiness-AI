"""Vendor pinned Swagger UI assets for offline API docs; preserve its license."""

import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
package = root / "apps/web/node_modules/swagger-ui-dist"
static = root / "apps/api/static"
static.mkdir(exist_ok=True)
for name in ["swagger-ui-bundle.js", "swagger-ui.css", "favicon-32x32.png", "LICENSE", "NOTICE"]:
    if (package / name).exists():
        shutil.copyfile(package / name, static / name)
version = json.loads((package / "package.json").read_text())["version"]
(static / "README.md").write_text(
    f"# Vendored API documentation assets\n\nSwagger UI {version}, Apache-2.0. Source: https://github.com/swagger-api/swagger-ui\n\nRegenerate from the locked frontend dependency with `python scripts/vendor_docs.py`. Only static assets are copied; install-time Scarf telemetry is explicitly disabled in pnpm-workspace.yaml. Swagger's remote validator is disabled at runtime.\n"
)
