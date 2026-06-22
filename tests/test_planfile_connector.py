# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import json
import tempfile

from urirun import v2
from urirun_connector_planfile import (
    connector_manifest,
    create_ticket,
    list_tickets,
    main,
    run_dsl,
    urirun_bindings,
)
from urirun_connector_planfile import _exec


_EXEC_PREFIX = ["python3", "-m", "urirun_connector_planfile._exec"]


def _compile_registry(bindings: dict):
    registry = v2.compile_registry(bindings)
    return registry, v2.list_routes(registry)


def test_bindings_use_exec_argv_template() -> None:
    bindings = urirun_bindings()["bindings"]
    # Representative route binding is an argv-template invoking the _exec module.
    binding = bindings["task://host/ticket/command/create"]
    assert binding["adapter"] == "argv-template"
    assert binding["argv"][:4] == [*_EXEC_PREFIX, "create"]


def test_bindings_shape_and_compile() -> None:
    bindings = urirun_bindings()
    json.dumps(bindings)
    assert bindings["version"] == "urirun.bindings.v2"
    assert "task://host/ticket/command/create" in bindings["bindings"]
    assert "planfile://host/dsl/command/run" in bindings["bindings"]
    registry, routes = _compile_registry(bindings)
    assert registry["version"] == "urirun.registry.v1"
    assert any(route["uri"] == "task://host/ticket/command/create" for route in routes)


def test_manifest_derives_routes_and_schemes() -> None:
    manifest = connector_manifest()
    assert manifest["id"] == "planfile"
    assert "task://host/ticket/command/create" in manifest["routes"]
    assert "planfile://host/dsl/command/run" in manifest["routes"]
    assert set(manifest["uriSchemes"]) == {"task", "planfile"}


def test_direct_planfile_operations() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        created = create_ticket(project=tmp, name="Connector ticket", prompt="check system", queue="daily")
        assert created["ok"] is True
        ticket_id = created["ticket"]["id"]

        listed = list_tickets(project=tmp, sprint="current", queue="daily")
        assert listed["ok"] is True
        assert listed["tickets"][0]["id"] == ticket_id

        dsl = run_dsl(project=tmp, command="list tickets sprint=current")
        assert dsl["ok"] is True
        assert dsl["result"]["ok"] is True


def test_exec_main_prints_json(capsys) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        rc = _exec.main(["create", "--project", tmp, "--name", "Exec ticket", "--queue", "daily"])
        assert rc == 0
        created = json.loads(capsys.readouterr().out)
        assert created["ok"] is True

        rc = _exec.main(["list", "--project", tmp, "--queue", "daily"])
        assert rc == 0
        listed = json.loads(capsys.readouterr().out)
        assert listed["tickets"][0]["name"] == "Exec ticket"


def test_main_bindings_and_manifest(capsys) -> None:
    assert main(["bindings"]) == 0
    bindings = json.loads(capsys.readouterr().out)
    assert "task://host/tickets/query/list" in bindings["bindings"]

    assert main(["manifest"]) == 0
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["id"] == "planfile"
    assert "planfile://host/dsl/command/run" in manifest["routes"]
