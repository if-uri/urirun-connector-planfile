# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""Planfile task routes for urirun — v2 authoring.

Each route is declared once with a typed ``@conn.handler``: the function
signature becomes the input schema and the body is the implementation — no argv
template, no ``_exec.py``, no ``run_action`` argv dispatcher. ``isolated=True``
runs each route out-of-process through the shared ``python -m urirun.exec``
runner, so the binding stays **registry-portable**: it executes from a
compiled/served registry (``urirun run`` / ``urirun node serve``) with only the
package importable — no console-script install and no per-connector shim.

Routes operate on a project directory:

* ``task://host/tickets/query/list``        -- list tickets in a sprint
* ``task://host/ticket/query/next``         -- next runnable ticket
* ``task://host/ticket/query/show``         -- show one ticket
* ``task://host/ticket/command/create``     -- create a ticket
* ``task://host/ticket/command/start``      -- start a ticket
* ``task://host/ticket/command/complete``   -- complete a ticket
* ``task://host/ticket/command/fail``       -- fail a ticket
* ``task://host/ticket/command/block``      -- block a ticket
* ``task://host/ticket/command/ready``      -- mark a ticket ready
* ``planfile://host/dsl/command/run``       -- run planfile DSL

The manifest stays prose-only; ``routes``/``uriSchemes`` are derived from the
declared routes.
"""

from __future__ import annotations

import json
from typing import Any

import urirun
from urirun.host import planfile_adapter as _pa

CONNECTOR_ID = "planfile"
conn = urirun.connector(CONNECTOR_ID, scheme="task")

# Reuse the urirun host planfile backend (single source of truth).
_imports = _pa._imports
project_root = _pa.project_root
load_planfile = _pa.load_planfile
ticket_to_dict = _pa.ticket_to_dict
build_ticket_payload = _pa.build_ticket_payload


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item.strip() for item in str(value).split(",") if item.strip()]


# --- route handlers: schema + implementation all derived ------------------

@conn.handler("tickets/query/list", isolated=True, meta={"label": "List planfile tickets"})
def list_tickets(project: str = ".", sprint: str = "current", status: str = "", label: str = "", queue: str = "") -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if status and status != "all":
        filters["status"] = status
    labels = _split_csv(label)
    if labels:
        filters["labels"] = labels
    tickets = [ticket_to_dict(t) for t in load_planfile(project).list_tickets(sprint=sprint, **filters)]
    if queue:
        tickets = [t for t in tickets if (t.get("execution") or {}).get("queue", "default") == queue]
    # Support archived view: if status=archive or sprint=archive, returns archived ones
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "tickets": tickets}


@conn.handler("ticket/query/next", isolated=True, meta={"label": "Get next runnable ticket"})
def next_ticket(project: str = ".", sprint: str = "current", queue: str = "") -> dict[str, Any]:
    ticket = load_planfile(project).next_ticket(sprint=sprint, queue=queue or None)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project),
            "ticket": ticket_to_dict(ticket) if ticket else None}


@conn.handler("ticket/query/show", isolated=True, meta={"label": "Show one ticket"})
def show_ticket(project: str = ".", ticket_id: str = "") -> dict[str, Any]:
    if not ticket_id:
        return urirun.fail("ticket_id is required", connector=CONNECTOR_ID)
    ticket = load_planfile(project).get_ticket(ticket_id)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project),
            "ticket": ticket_to_dict(ticket) if ticket else None}


@conn.handler("ticket/command/create", isolated=True, meta={"label": "Create planfile ticket"})
def create_ticket(project: str = ".", name: str = "", description: str = "", priority: str = "normal",
                  labels: str = "", queue: str = "default", prompt: str = "", executor_handler: str = "",
                  max_attempts: int = 1) -> dict[str, Any]:
    if not name:
        return urirun.fail("name is required", connector=CONNECTOR_ID)
    payload: dict[str, Any] = {"name": name, "description": description, "priority": priority,
                               "labels": labels, "queue": queue, "prompt": prompt, "max_attempts": max_attempts}
    if executor_handler:
        payload["executor_handler"] = executor_handler
    ticket = load_planfile(project).create_ticket(**build_ticket_payload(payload))
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket)}


def update_status(project: str, ticket_id: str, status: str, note: str = "", result_json: str = "",
                  artifacts: str = "", error: str = "", reason: str = "", actor: str = "") -> dict[str, Any]:
    if not ticket_id:
        return urirun.fail("ticket_id is required", connector=CONNECTOR_ID)
    pf = load_planfile(project)
    r = reason or note or ""
    a = actor or ""
    if status == "start":
        ticket = pf.start_ticket(ticket_id, reason=r or None, actor=a or None)
    elif status == "complete":
        result = json.loads(result_json) if result_json else None
        ticket = pf.complete_ticket(ticket_id, note=note or None, result=result, artifacts=_split_csv(artifacts), reason=r or None, actor=a or None)
    elif status == "fail":
        ticket = pf.fail_ticket(ticket_id, error or "failed", reason=r or None, actor=a or None)
    elif status == "block":
        if hasattr(pf, "block_ticket"):
            ticket = pf.block_ticket(ticket_id, reason=r or note or "BLOCKED", actor=a or None)
        else:
            ticket = pf.update_ticket(ticket_id, status="blocked", description=note or "BLOCKED", reason=r or None, actor=a or None)
    elif status == "ready":
        ticket = pf.ready_ticket(ticket_id, note=note or None, reason=r or None, actor=a or None)
    else:
        return urirun.fail(f"unsupported status action: {status}", connector=CONNECTOR_ID)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket)}


@conn.handler("ticket/command/start", isolated=True, meta={"label": "Start ticket"})
def start(project: str = ".", ticket_id: str = "") -> dict[str, Any]:
    return update_status(project, ticket_id, "start")


@conn.handler("ticket/command/complete", isolated=True, meta={"label": "Complete ticket"})
def complete(project: str = ".", ticket_id: str = "", note: str = "", result_json: str = "", artifacts: str = "", reason: str = "", actor: str = "") -> dict[str, Any]:
    return update_status(project, ticket_id, "complete", note=note, result_json=result_json, artifacts=artifacts, reason=reason, actor=actor)


@conn.handler("ticket/command/fail", isolated=True, meta={"label": "Fail ticket"})
def fail(project: str = ".", ticket_id: str = "", error: str = "failed", reason: str = "", actor: str = "") -> dict[str, Any]:
    return update_status(project, ticket_id, "fail", error=error, reason=reason, actor=actor)


@conn.handler("ticket/command/block", isolated=True, meta={"label": "Block ticket"})
def block(project: str = ".", ticket_id: str = "", note: str = "BLOCKED", reason: str = "", actor: str = "") -> dict[str, Any]:
    return update_status(project, ticket_id, "block", note=note, reason=reason, actor=actor)


@conn.handler("ticket/command/ready", isolated=True, meta={"label": "Mark ticket ready"})
def ready(project: str = ".", ticket_id: str = "", note: str = "", reason: str = "", actor: str = "") -> dict[str, Any]:
    return update_status(project, ticket_id, "ready", note=note, reason=reason, actor=actor)


@conn.handler("ticket/command/archive", isolated=True, meta={"label": "Archive ticket to 'archive' sprint (hides from main dashboard view)"})
def archive(project: str = ".", ticket_id: str = "", note: str = "", reason: str = "", actor: str = "") -> dict[str, Any]:
    if not ticket_id:
        return urirun.fail("ticket_id is required", connector=CONNECTOR_ID)
    from urirun.host import planfile_adapter as pa
    t = pa.archive_ticket(project, ticket_id, note=note or None, reason=reason or None, actor=actor or None)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project),
            "ticket": t, "archived": True}


# Declared with the full URI (different scheme) but bound to this connector id so
# urirun_bindings() exports it alongside the task:// routes.
@conn.handler("planfile://host/dsl/command/run", isolated=True, meta={"label": "Run planfile DSL"})
def run_dsl(project: str = ".", command: str = "") -> dict[str, Any]:
    if not command:
        return urirun.fail("command is required", connector=CONNECTOR_ID)
    result = _imports()["DSLExecutor"](project_root(project)).run(command)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "result": result.to_dict()}


# --- authoring surface: bindings / manifest / CLI --------------------------

def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings)."""
    return conn.bindings()


def connector_manifest() -> dict[str, Any]:
    """Full manifest: prose (connector.manifest.json) + routes/uriSchemes/
    adapterKinds/examples derived from the handlers."""
    return conn.manifest(urirun.load_manifest(__package__))


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point: subcommands + dispatch derived from the handlers."""
    return conn.cli(argv, manifest_prose=urirun.load_manifest(__package__))


if __name__ == "__main__":
    import sys

    raise SystemExit(main())
