"""Run against an already started Compose stack. Uses only the Python standard library."""

import json
import os
import urllib.request
from uuid import uuid4

base = os.getenv("SMOKE_BASE_URL", "http://localhost:8080")


def call(path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "Idempotency-Key": str(uuid4())}
    with urllib.request.urlopen(
        urllib.request.Request(base + path, data=body, headers=headers), timeout=30
    ) as response:
        return json.load(response)


assert call("/health/ready")["status"] == "ready"
p = call("/api/v1/portfolio")
assert len(p["markets"]) == 14
s = call("/api/v1/scenarios", {"name": "Compose smoke", "accelerate_days": 7})
assert s["id"] != p["id"]
assert call("/api/v1/portfolio")["id"] == p["id"]
assert call("/api/v1/transfers", {})
assert call("/api/v1/briefs", {})["statements"]
print("PASS: Compose persistence/API/scenario/transfers/brief workflow")
