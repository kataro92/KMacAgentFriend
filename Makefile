.PHONY: dev install test lint health

dev:
	./scripts/dev_run.sh

install:
	@if [ -d .venv ] && ! .venv/bin/python -c 'import sys' 2>/dev/null; then \
		echo "Removing stale .venv (project moved or Python upgraded)..."; \
		rm -rf .venv; \
	fi
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt
	.venv/bin/pip install -e .

test:
	.venv/bin/pytest -q

lint:
	.venv/bin/ruff check agent tests

health:
	@token=$$(.venv/bin/python -c "from kmac_agent_friend.config import get_settings, resolve_api_token; get_settings.cache_clear(); print(resolve_api_token(get_settings()))"); \
	curl -sf -H "Authorization: Bearer $$token" http://127.0.0.1:18750/health | .venv/bin/python -m json.tool
