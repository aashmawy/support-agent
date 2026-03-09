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
	python -m garak --target_type openai --target_name gpt-4o-mini --probes promptinject --model_type chat 2>/dev/null || echo "Run garak with OPENAI_API_KEY set; see README and blog."

trajectly-record:
	python -m trajectly record trajectly/specs/*.agent.yaml --project-root .

trajectly-run:
	python -m trajectly run trajectly/specs/*.agent.yaml --project-root .

lint:
	ruff check app tests scripts
