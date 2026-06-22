#!/usr/bin/env bash
# planfile: install once, then just run — no compile, no registry path.
set -euo pipefail

# 1) declare what to install (catalog id or package name; --catalog points at a
#    local/on-prem registry instead of the default connect.ifuri.com)
urirun install urirun-connector-planfile        # local dev: pip install -e .

# 2) declare what to run (urirun auto-discovers installed connectors)
urirun run 'task://host/tickets/query/list' --payload '{}' --execute --allow 'task://*'
