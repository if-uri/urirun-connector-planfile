# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import argparse
import json
import sys

from .core import connector_manifest, run_action, urirun_bindings


def emit(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", default=".")


def _add_ticket_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ticket-id", default="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="urirun-planfile")
    sub = parser.add_subparsers(dest="command", required=True)

    list_parser = sub.add_parser("list", help="List planfile tickets")
    _add_common(list_parser)
    list_parser.add_argument("--sprint", default="current")
    list_parser.add_argument("--status", default="")
    list_parser.add_argument("--label", default="")
    list_parser.add_argument("--queue", default="")

    next_parser = sub.add_parser("next", help="Get next runnable ticket")
    _add_common(next_parser)
    next_parser.add_argument("--sprint", default="current")
    next_parser.add_argument("--queue", default="")

    show_parser = sub.add_parser("show", help="Show one ticket")
    _add_common(show_parser)
    _add_ticket_id(show_parser)

    create_parser = sub.add_parser("create", help="Create a ticket")
    _add_common(create_parser)
    create_parser.add_argument("--name", required=True)
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--priority", default="normal")
    create_parser.add_argument("--labels", default="")
    create_parser.add_argument("--queue", default="default")
    create_parser.add_argument("--prompt", default="")
    create_parser.add_argument("--executor-handler", default="")
    create_parser.add_argument("--max-attempts", type=int, default=1)

    for name in ("start", "block", "ready"):
        action_parser = sub.add_parser(name, help=f"{name} a ticket")
        _add_common(action_parser)
        _add_ticket_id(action_parser)
        if name in {"block", "ready"}:
            action_parser.add_argument("--note", default="BLOCKED" if name == "block" else "")

    complete_parser = sub.add_parser("complete", help="Complete a ticket")
    _add_common(complete_parser)
    _add_ticket_id(complete_parser)
    complete_parser.add_argument("--note", default="")
    complete_parser.add_argument("--result-json", default="")
    complete_parser.add_argument("--artifacts", default="")

    fail_parser = sub.add_parser("fail", help="Fail a ticket")
    _add_common(fail_parser)
    _add_ticket_id(fail_parser)
    fail_parser.add_argument("--error", default="failed")

    dsl_parser = sub.add_parser("dsl", help="Run planfile DSL")
    _add_common(dsl_parser)
    dsl_parser.add_argument("--command", required=True)

    sub.add_parser("manifest", help="Emit connect.ifuri.com connector manifest")
    sub.add_parser("bindings", help="Emit urirun v2 bindings")

    args = parser.parse_args(argv)
    data = vars(args)
    command = data.pop("command")
    if command == "manifest":
        emit(connector_manifest())
        return 0
    if command == "bindings":
        emit(urirun_bindings())
        return 0
    try:
        result = run_action(command, **data)
    except Exception as exc:  # noqa: BLE001 - CLI reports connector failures as JSON.
        emit({"ok": False, "connector": "planfile", "action": command, "error": str(exc)})
        return 2
    emit(result)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
