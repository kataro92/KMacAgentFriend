.PHONY: dev install test lint health

dev:
	./scripts/dev_run.sh

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check agent tests

health:
	@set -a && [ -f .env ] && . ./.env && set +a; \
	token=$${KAF_API_TOKEN:-$$(cat "$$HOME/Library/Application Support/KMacAgentFriend/.api_token" 2>/dev/null)}; \
	curl -sf -H "Authorization: Bearer $$token" http://127.0.0.1:18750/health | python3 -m json.tool
