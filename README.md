# urirun connector: Planfile

Planfile connector exposes task operations as URI commands for `urirun` and
ifURI.

Routes:

- `task://host/tickets/query/list`
- `task://host/ticket/query/next`
- `task://host/ticket/query/show`
- `task://host/ticket/command/create`
- `task://host/ticket/command/start`
- `task://host/ticket/command/complete`
- `task://host/ticket/command/fail`
- `task://host/ticket/command/block`
- `task://host/ticket/command/ready`
- `planfile://host/dsl/command/run`

Install from GitHub:

```bash
pip install "git+https://github.com/if-uri/urirun-connector-planfile.git@v0.1.1"
```

Use directly:

```bash
urirun-planfile create --project . --name "Daily domain check" --queue daily
urirun-planfile list --project . --queue daily
urirun-planfile bindings > planfile.bindings.json
urirun compile planfile.bindings.json --out planfile.registry.json
urirun run 'task://host/tickets/query/list' planfile.registry.json \
  --payload '{"project":".","queue":"daily"}' \
  --execute --allow 'task://host/*'
```

The bindings are generated from decorator declarations in
`urirun_connector_planfile.core`; the Planfile runtime is owned by this
connector package instead of the `urirun` core runtime.
