#!/usr/bin/env bash
# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

set -euo pipefail

mkdir -p .docker-smoke
PROJECT_DIR="$(mktemp -d)"

echo "==> direct connector CLI"
urirun-planfile create --project "$PROJECT_DIR" --name "Docker ticket" --queue daily > .docker-smoke/create.json
urirun-planfile list --project "$PROJECT_DIR" --queue daily > .docker-smoke/list.json

echo "==> build bindings and registry"
python3 - <<'PY' > .docker-smoke/bindings.json
import json
from urirun_connector_planfile import urirun_bindings
print(json.dumps(urirun_bindings(), indent=2))
PY

urirun validate .docker-smoke/bindings.json
urirun compile .docker-smoke/bindings.json --out .docker-smoke/registry.json

echo "==> execute connector URI through urirun"
urirun run 'task://host/tickets/query/list' .docker-smoke/registry.json \
  --payload "{\"project\":\"$PROJECT_DIR\",\"queue\":\"daily\"}" \
  --execute \
  --allow 'task://host/*' > .docker-smoke/urirun-result.json

echo "==> project registry to MCP tools and A2A card"
python3 -m urirun.v2_mcp tools .docker-smoke/registry.json > .docker-smoke/mcp-tools.json
python3 -m urirun.v2_mcp card .docker-smoke/registry.json \
  --name planfile-docker \
  --url http://tester/ > .docker-smoke/a2a-card.json

python3 - <<'PY'
import json
from pathlib import Path

base = Path(".docker-smoke")
created = json.loads((base / "create.json").read_text())
listed = json.loads((base / "list.json").read_text())
run = json.loads((base / "urirun-result.json").read_text())
run_payload = json.loads(run["result"]["stdout"])
tools = json.loads((base / "mcp-tools.json").read_text())
card = json.loads((base / "a2a-card.json").read_text())

assert created["ok"] is True, created
assert listed["tickets"][0]["name"] == "Docker ticket", listed
assert run["ok"] is True, run
assert run_payload["tickets"][0]["name"] == "Docker ticket", run_payload
assert any(tool["name"] == "task_host_tickets_query" for tool in tools["tools"]), tools
assert any("task://host/tickets/query/list" in skill.get("examples", []) for skill in card["skills"]), card
print(json.dumps({
    "ok": True,
    "mcpTools": len(tools["tools"]),
    "a2aSkills": len(card["skills"]),
}, indent=2))
PY
