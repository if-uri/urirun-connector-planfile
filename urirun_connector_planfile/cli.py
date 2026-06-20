# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.

from __future__ import annotations

import argparse
import sys

import urirun

from .core import connector_manifest, run_action, urirun_bindings




def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project", default=".")


def _add_ticket_id(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ticket-id", default="")


def register(sub) -> None:

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


def dispatch(args) -> int:
    data = vars(args)
    command = data.pop("command")
    try:
        result = run_action(command, **data)
    except Exception as exc:  # noqa: BLE001 - connector CLI reports JSON errors.
        urirun.connector_emit({"ok": False, "connector": "planfile", "action": command, "error": str(exc)})
        return 2
    urirun.connector_emit(result)
    return 0 if result.get("ok") else 2


def main(argv: list[str] | None = None) -> int:
    return urirun.connector_cli(
        "urirun-planfile",
        manifest=connector_manifest,
        bindings=urirun_bindings,
        register=register,
        dispatch=dispatch,
        argv=argv,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
