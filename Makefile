.PHONY: install init-db generate-data run test test-unit test-property test-component test-integration eval-promptfoo eval-garak trajectly-record trajectly-run lint

install:
	pip install -e ".[dev]"

init-db:
	python scripts/init_db.py

generate-data:
	python scripts/generate_data.py

run:
	python -m app.main --query "$(QUERY)"

test: test-unit test-property test-component test-integration

test-unit:
	pytest tests/unit -v

test-property:
	pytest tests/property -v

test-component:
	pytest tests/component -v

test-integration:
	pytest tests/integration -v

eval-promptfoo:
	npx promptfoo@latest eval -c evals/promptfoo.yaml

eval-garak:
	@set -a; [ -f .env ] && . ./.env; set +a; \
	XDG_CONFIG_HOME="$$PWD/.xdg/config" \
	XDG_DATA_HOME="$$PWD/.xdg/data" \
	XDG_CACHE_HOME="$$PWD/.xdg/cache" \
	python -m garak --model_type openai --model_name gpt-4o-mini --probes promptinject || { \
		status=$$?; \
		if [ -z "$$OPENAI_API_KEY" ]; then \
			echo "OPENAI_API_KEY is not set. Copy .env.example to .env or export it in your shell."; \
		fi; \
		exit $$status; \
	}

trajectly-record:
	python -m trajectly record trajectly/specs/*.agent.yaml --project-root .

trajectly-run:
	python -m trajectly run trajectly/specs/*.agent.yaml --project-root .

lint:
	ruff check app tests scripts
