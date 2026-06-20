from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import urirun
from urirun_connector_planfile import connector_manifest, create_ticket, list_tickets, run_dsl, urirun_bindings
from urirun_connector_planfile.cli import main


def _compile_registry(bindings: dict):
    registry = urirun.compile_registry(bindings)
    return registry, urirun.list_routes(registry)


def test_manifest_shape() -> None:
    manifest = connector_manifest()
    assert manifest["id"] == "planfile"
    assert "task://host/ticket/command/create" in manifest["routes"]
    assert "planfile://host/dsl/command/run" in manifest["routes"]


def test_bindings_shape_and_compile() -> None:
    bindings = urirun_bindings()
    json.dumps(bindings)
    assert bindings["version"] == "urirun.bindings.v2"
    assert "task://host/ticket/command/create" in bindings["bindings"]
    assert "planfile://host/dsl/command/run" in bindings["bindings"]
    registry, routes = _compile_registry(bindings)
    assert registry["version"] == "urirun.registry.v1"
    assert any(route["uri"] == "task://host/ticket/command/create" for route in routes)


def test_direct_planfile_operations() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        created = create_ticket(project=tmp, name="Connector ticket", prompt="check system", queue="daily")
        assert created["ok"] is True
        ticket_id = created["ticket"]["id"]

        listed = list_tickets(project=tmp, sprint="current", queue="daily")
        assert listed["tickets"][0]["id"] == ticket_id

        dsl = run_dsl(project=tmp, command='list tickets sprint=current')
        assert dsl["ok"] is True
        assert dsl["result"]["ok"] is True


def test_cli_create_list_and_bindings(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        assert main(["create", "--project", tmp, "--name", "CLI ticket", "--queue", "daily"]) == 0
        created = json.loads(capsys.readouterr().out)
        assert created["ok"] is True

        assert main(["list", "--project", tmp, "--queue", "daily"]) == 0
        listed = json.loads(capsys.readouterr().out)
        assert listed["tickets"][0]["name"] == "CLI ticket"

        assert main(["bindings"]) == 0
        bindings = json.loads(capsys.readouterr().out)
        assert "task://host/tickets/query/list" in bindings["bindings"]


def test_urirun_executes_planfile_connector_uri() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp) / "bin"
        bin_dir.mkdir()
        wrapper = bin_dir / "urirun-planfile"
        wrapper.write_text(
            f"#!/usr/bin/env sh\nexec {sys.executable} -m urirun_connector_planfile.cli \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(0o755)
        previous_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{bin_dir}{os.pathsep}{previous_path}"
        registry, _routes = _compile_registry(urirun_bindings())
        try:
            create_result = urirun.run(
                "task://host/ticket/command/create",
                registry,
                {"project": tmp, "name": "URI ticket", "queue": "daily"},
                mode="execute",
                policy={"execute": {"allow": ["task://host/*"]}},
            )
            assert create_result["ok"] is True, create_result
            stdout = json.loads(create_result["result"]["stdout"])
            assert stdout["ticket"]["name"] == "URI ticket"

            list_result = urirun.run(
                "task://host/tickets/query/list",
                registry,
                {"project": tmp, "queue": "daily"},
                mode="execute",
                policy={"execute": {"allow": ["task://host/*"]}},
            )
            assert list_result["ok"] is True, list_result
            listed = json.loads(list_result["result"]["stdout"])
            assert listed["tickets"][0]["name"] == "URI ticket"
        finally:
            os.environ["PATH"] = previous_path
