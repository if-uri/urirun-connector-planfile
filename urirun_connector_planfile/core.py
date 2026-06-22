# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

"""Planfile task routes for urirun.

Each route is declared once with ``@TASK_CONNECTOR.command`` / ``@urirun.command``:
the function signature becomes the input schema and the body returns the ``argv``
template urirun runs. The template invokes this package's ``_exec`` module
out-of-process (``python3 -m urirun_connector_planfile._exec <subcommand> ...``),
so the route works through the file-based registry CLI (``urirun compile`` /
``urirun run``) WITHOUT this connector being pip-installed -- as well as the
in-process Python helpers (``list_tickets``, ``create_ticket``, ...) that
``_exec`` and the tests call directly through ``run_action``.

The manifest stays prose-only; ``routes``/``uriSchemes`` are derived from the
declared routes.
"""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

import urirun
from urirun.host import planfile_adapter as _pa


CONNECTOR_ID = "planfile"
TASK_CONNECTOR = urirun.connector(CONNECTOR_ID, scheme="task")

# argv prefix the compiled registry uses to execute a route out-of-process.
_EXEC = ["python3", "-m", "urirun_connector_planfile._exec"]


# Reuse the urirun host planfile backend (single source of truth) instead of
# duplicating the planfile library wrappers.
_imports = _pa._imports
project_root = _pa.project_root
load_planfile = _pa.load_planfile
_model_dict = _pa._model_dict
ticket_to_dict = _pa.ticket_to_dict
normalize_priority = _pa.normalize_priority
build_ticket_payload = _pa.build_ticket_payload


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    return [item.strip() for item in str(value).split(",") if item.strip()]


# --- route logic (real implementation) ------------------------------------

def list_tickets(project: str = ".", sprint: str = "current", status: str = "", label: str = "", queue: str = "") -> dict[str, Any]:
    filters: dict[str, Any] = {}
    if status and status != "all":
        filters["status"] = status
    labels = _split_csv(label)
    if labels:
        filters["labels"] = labels
    tickets = [ticket_to_dict(ticket) for ticket in load_planfile(project).list_tickets(sprint=sprint, **filters)]
    if queue:
        tickets = [
            ticket
            for ticket in tickets
            if (ticket.get("execution") or {}).get("queue", "default") == queue
        ]
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "tickets": tickets}


def next_ticket(project: str = ".", sprint: str = "current", queue: str = "") -> dict[str, Any]:
    ticket = load_planfile(project).next_ticket(sprint=sprint, queue=queue or None)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket) if ticket else None}


def show_ticket(project: str = ".", ticket_id: str = "") -> dict[str, Any]:
    if not ticket_id:
        raise ValueError("ticket_id is required")
    ticket = load_planfile(project).get_ticket(ticket_id)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket) if ticket else None}


def create_ticket(
    project: str = ".",
    name: str = "",
    description: str = "",
    priority: str = "normal",
    labels: str = "",
    queue: str = "default",
    prompt: str = "",
    executor_handler: str = "",
    max_attempts: int = 1,
) -> dict[str, Any]:
    if not name:
        raise ValueError("name is required")
    payload: dict[str, Any] = {
        "name": name,
        "description": description,
        "priority": priority,
        "labels": labels,
        "queue": queue,
        "prompt": prompt,
        "max_attempts": max_attempts,
    }
    if executor_handler:
        payload["executor_handler"] = executor_handler
    ticket = load_planfile(project).create_ticket(**build_ticket_payload(payload))
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket)}


def update_status(project: str, ticket_id: str, status: str, note: str = "", result_json: str = "", artifacts: str = "", error: str = "") -> dict[str, Any]:
    if not ticket_id:
        raise ValueError("ticket_id is required")
    pf = load_planfile(project)
    if status == "start":
        ticket = pf.start_ticket(ticket_id)
    elif status == "complete":
        result = json.loads(result_json) if result_json else None
        ticket = pf.complete_ticket(ticket_id, note=note or None, result=result, artifacts=_split_csv(artifacts))
    elif status == "fail":
        ticket = pf.fail_ticket(ticket_id, error or "failed")
    elif status == "block":
        ticket = pf.update_ticket(ticket_id, status="blocked", description=note or "BLOCKED")
    elif status == "ready":
        ticket = pf.ready_ticket(ticket_id, note=note or None)
    else:
        raise ValueError(f"unsupported status action: {status}")
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "ticket": ticket_to_dict(ticket)}


def run_dsl(project: str = ".", command: str = "") -> dict[str, Any]:
    if not command:
        raise ValueError("command is required")
    result = _imports()["DSLExecutor"](project_root(project)).run(command)
    return {"ok": True, "connector": CONNECTOR_ID, "project": project_root(project), "result": result.to_dict()}


# --- shared dispatch (CLI execute path + out-of-process _exec) -------------

def run_action(action: str, **kwargs: Any) -> dict[str, Any]:
    if action == "list":
        return list_tickets(**kwargs)
    if action == "next":
        return next_ticket(**kwargs)
    if action == "show":
        return show_ticket(**kwargs)
    if action == "create":
        return create_ticket(**kwargs)
    if action in {"start", "complete", "fail", "block", "ready"}:
        return update_status(status=action, **kwargs)
    if action == "dsl":
        return run_dsl(**kwargs)
    raise ValueError(f"unsupported action: {action}")


# --- route declarations: schema + argv template all derived ---------------

@TASK_CONNECTOR.command("tickets/query/list", meta={"label": "List planfile tickets"})
def list_command(project: str = ".", sprint: str = "current", status: str = "", label: str = "", queue: str = "") -> list[str]:
    return [*_EXEC, "list", "--project", "{project}", "--sprint", "{sprint}", "--status", "{status}", "--label", "{label}", "--queue", "{queue}"]


@TASK_CONNECTOR.command("ticket/query/next", meta={"label": "Get next runnable ticket"})
def next_command(project: str = ".", sprint: str = "current", queue: str = "") -> list[str]:
    return [*_EXEC, "next", "--project", "{project}", "--sprint", "{sprint}", "--queue", "{queue}"]


@TASK_CONNECTOR.command("ticket/query/show", meta={"label": "Show one ticket"})
def show_command(project: str = ".", ticket_id: str = "") -> list[str]:
    return [*_EXEC, "show", "--project", "{project}", "--ticket-id", "{ticket_id}"]


@TASK_CONNECTOR.command("ticket/command/create", meta={"label": "Create planfile ticket"})
def create_command(
    project: str = ".",
    name: str = "",
    description: str = "",
    priority: str = "normal",
    labels: str = "",
    queue: str = "default",
    prompt: str = "",
    executor_handler: str = "",
    max_attempts: int = 1,
) -> list[str]:
    return [
        *_EXEC,
        "create",
        "--project",
        "{project}",
        "--name",
        "{name}",
        "--description",
        "{description}",
        "--priority",
        "{priority}",
        "--labels",
        "{labels}",
        "--queue",
        "{queue}",
        "--prompt",
        "{prompt}",
        "--executor-handler",
        "{executor_handler}",
        "--max-attempts",
        "{max_attempts}",
    ]


@TASK_CONNECTOR.command("ticket/command/start", meta={"label": "Start ticket"})
def start_command(project: str = ".", ticket_id: str = "") -> list[str]:
    return [*_EXEC, "start", "--project", "{project}", "--ticket-id", "{ticket_id}"]


@TASK_CONNECTOR.command("ticket/command/complete", meta={"label": "Complete ticket"})
def complete_command(project: str = ".", ticket_id: str = "", note: str = "", result_json: str = "", artifacts: str = "") -> list[str]:
    return [*_EXEC, "complete", "--project", "{project}", "--ticket-id", "{ticket_id}", "--note", "{note}", "--result-json", "{result_json}", "--artifacts", "{artifacts}"]


@TASK_CONNECTOR.command("ticket/command/fail", meta={"label": "Fail ticket"})
def fail_command(project: str = ".", ticket_id: str = "", error: str = "failed") -> list[str]:
    return [*_EXEC, "fail", "--project", "{project}", "--ticket-id", "{ticket_id}", "--error", "{error}"]


@TASK_CONNECTOR.command("ticket/command/block", meta={"label": "Block ticket"})
def block_command(project: str = ".", ticket_id: str = "", note: str = "BLOCKED") -> list[str]:
    return [*_EXEC, "block", "--project", "{project}", "--ticket-id", "{ticket_id}", "--note", "{note}"]


@TASK_CONNECTOR.command("ticket/command/ready", meta={"label": "Mark ticket ready"})
def ready_command(project: str = ".", ticket_id: str = "", note: str = "") -> list[str]:
    return [*_EXEC, "ready", "--project", "{project}", "--ticket-id", "{ticket_id}", "--note", "{note}"]


@urirun.command("planfile://host/dsl/command/run", meta={"connector": CONNECTOR_ID, "label": "Run planfile DSL", "cliAlias": "dsl"})
def dsl_command(project: str = ".", command: str = "") -> list[str]:
    return [*_EXEC, "dsl", "--project", "{project}", "--command", "{command}"]


# --- authoring surface: bindings / manifest / CLI --------------------------

def urirun_bindings() -> dict[str, Any]:
    """Serializable v2 bindings for this connector (entry point: urirun.bindings)."""
    return urirun.connector_bindings(connector=CONNECTOR_ID)


def connector_manifest() -> dict[str, Any]:
    """Manifest prose (connector.manifest.json) merged with the derived route set."""
    text = resources.files(__package__).joinpath("connector.manifest.json").read_text(encoding="utf-8")
    manifest = json.loads(text)
    bindings = urirun_bindings()["bindings"]
    manifest["routes"] = sorted(bindings)
    manifest["uriSchemes"] = sorted({uri.split("://", 1)[0] for uri in bindings})
    return manifest


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point: ``bindings``/``manifest`` plus the route
    subcommands (delegated to the out-of-process executor)."""
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "bindings":
        print(json.dumps(urirun_bindings(), indent=2))
        return 0
    if args and args[0] == "manifest":
        print(json.dumps(connector_manifest(), indent=2))
        return 0
    from ._exec import main as _exec_main

    return _exec_main(args)


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
