# Author: Tom Sapletta · https://tom.sapletta.com
# Part of the ifURI solution.
"""Conformance gate for the planfile connector's route contracts.

Pure file-backed I/O → the gate runs the REAL ticket lifecycle against a temp project and asserts
each live envelope conforms to its contract (code↔contract by execution, the strongest gate).
"""
from __future__ import annotations

import urirun_connector_planfile.core as core
from urirun_connector_planfile.contracts import CONTRACTS
from urirun_connectors_toolkit.contract_gate import conform, envelope_violation


def test_contracts_conform():
    conform(CONTRACTS)


def test_every_route_has_a_contract():
    live = set(core.urirun_bindings()["bindings"])
    contracted = set(CONTRACTS)
    assert not (contracted - live), f"contracts point at missing routes: {sorted(contracted - live)}"
    assert not (live - contracted), f"routes without a contract: {sorted(live - contracted)}"


def test_live_lifecycle_conforms_to_contract(tmp_path):
    """Run the real ticket lifecycle and assert every envelope conforms to its contract."""
    proj = str(tmp_path)

    def conforms(uri, env):
        bad = envelope_violation(CONTRACTS[uri], env)
        assert bad is None, f"{uri}: live output violates contract: {bad}\nenvelope={env}"

    cr = core.create_ticket(project=proj, name="Test ticket", description="d")
    conforms("task://host/ticket/command/create", cr)
    tid = cr["ticket"]["id"]

    conforms("task://host/tickets/query/list", core.list_tickets(project=proj))
    conforms("task://host/ticket/query/next", core.next_ticket(project=proj))
    conforms("task://host/ticket/query/show", core.show_ticket(project=proj, ticket_id=tid))
    conforms("task://host/ticket/command/start", core.start(project=proj, ticket_id=tid))
    conforms("task://host/ticket/command/complete", core.complete(project=proj, ticket_id=tid, note="done"))
    conforms("planfile://host/dsl/command/run", core.run_dsl(project=proj, command="list"))

    # a fresh ticket for the fail/block/ready transitions
    t2 = core.create_ticket(project=proj, name="Second")["ticket"]["id"]
    conforms("task://host/ticket/command/block", core.block(project=proj, ticket_id=t2, note="waiting"))
    conforms("task://host/ticket/command/ready", core.ready(project=proj, ticket_id=t2))
    conforms("task://host/ticket/command/fail", core.fail(project=proj, ticket_id=t2, error="boom"))
