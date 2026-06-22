# planfile connector — example

Two lines: install, then run. `urirun run` auto-discovers every installed connector
via the `urirun.bindings` entry points, so there is no compile step or registry path.

```bash
urirun install urirun-connector-planfile
urirun run 'task://host/tickets/query/list' --payload '{}' --allow 'task://*'
```

`urirun install` resolves catalog ids through connect.ifuri.com (`--catalog <url>`
for an on-prem registry) and falls back to a direct `pip install` for a full
package name / git URL / local path. Inspect the live runtime any time with
`urirun run 'registry://local/routes/query/list'` (no path — it lists every
installed connector, like `error://` / `log://`).
