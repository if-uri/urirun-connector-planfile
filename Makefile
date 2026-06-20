.PHONY: help manifest bindings smoke test docker-test

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'

manifest: ## Print connector manifest
	python3 -m urirun_connector_planfile.cli manifest

bindings: ## Print urirun bindings
	python3 -m urirun_connector_planfile.cli bindings

smoke: ## Run CLI, registry, MCP and A2A smoke locally
	tmp=$$(mktemp -d); \
	mkdir -p "$$tmp/bin"; \
	printf '%s\n' '#!/usr/bin/env sh' 'exec python3 -m urirun_connector_planfile.cli "$$@"' > "$$tmp/bin/urirun-planfile"; \
	chmod +x "$$tmp/bin/urirun-planfile"; \
	export PATH="$$tmp/bin:$$PATH"; \
	python3 -m urirun_connector_planfile.cli create --project "$$tmp" --name "Smoke ticket" --queue daily; \
	python3 -m urirun_connector_planfile.cli list --project "$$tmp" --queue daily; \
	python3 -m urirun_connector_planfile.cli bindings > "$$tmp/bindings.json"; \
	urirun validate "$$tmp/bindings.json"; \
	urirun compile "$$tmp/bindings.json" --out "$$tmp/registry.json"; \
	urirun run 'task://host/tickets/query/list' "$$tmp/registry.json" \
	  --payload "{\"project\":\"$$tmp\",\"queue\":\"daily\"}" --execute --allow 'task://host/*' > "$$tmp/run.json"; \
	python3 -c 'import json,sys; data=json.load(open(sys.argv[1])); assert data["ok"], data; assert "Smoke ticket" in data["result"]["stdout"]' "$$tmp/run.json"; \
	python3 -m urirun.v2_mcp tools "$$tmp/registry.json"; \
	python3 -m urirun.v2_mcp card "$$tmp/registry.json" --name planfile --url http://localhost/

test: ## Run connector tests
	python3 -m pytest -q

docker-test: ## Run connector in Docker and verify registry, MCP and A2A
	docker compose up --build --abort-on-container-exit --exit-code-from tester
	docker compose down -v --remove-orphans
