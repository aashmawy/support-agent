# Support Agent

A realistic B2B SaaS support operations agent that answers questions from a local documentation corpus, looks up accounts, invoices, subscriptions, and tickets in SQLite, and uses internal tools for actions like invoice lookup, subscription inspection, MFA reset drafts, ticket escalation, and human approval requests. It refuses unsafe or unauthorized actions and escalates sensitive cases. Built with Python, LangChain, the OpenAI API, and deterministic guardrails.

## Architecture

```
User message
  → agent.py (orchestration loop)
    → guardrails.py  (refuse injection / require approval / require escalation)
    → retrieval.py   (search data/docs, sanitize snippets)
    → LangChain ChatOpenAI (tool calling, gpt-4o-mini)
    → tools.py       (check_invoice_status, inspect_subscription, ...)
      → db.py        (SQLite queries)
    → loop until done
  → AgentResponse (final_text, escalated, refused, tools_used)
```

- **agent.py** — Orchestration loop using LangChain (`ChatOpenAI` + tool binding) when `OPENAI_API_KEY` is set. Tests pass a mocked OpenAI client directly.
- **guardrails.py** — Deterministic policy in code: refuse injection/override/credential requests; require approval for MFA reset; require escalation for enterprise/sensitive actions; allow/deny tools by role.
- **retrieval.py** — Loads markdown from `data/docs/`, keyword search, returns top-k snippets. Sanitizes dangerous phrases (e.g. "ignore previous instructions") before injecting into the prompt.
- **tools.py** — Five tools: `check_invoice_status`, `inspect_subscription`, `draft_mfa_reset_request`, `escalate_ticket`, `request_human_approval`. All backed by `db.py`; no LLM inside tools.
- **db.py** — SQLite connection and parameterized queries. Schema in `app/schema.sql`.

## Repository structure

```
app/
  __init__.py          config.py           db.py
  schema.sql           models.py           retrieval.py
  tools.py             guardrails.py       agent.py
  main.py              helpers.py
data/
  docs/                # billing.md, mfa.md, refunds.md, escalation.md, security.md
  generated/           # accounts.json, subscriptions.json, invoices.json, tickets.json,
                       # eval_cases.json, trajectory_cases.json
scripts/
  generate_data.py     # deterministic fixture generation (seed-based)
  init_db.py           # create SQLite schema + load generated JSON
tests/
  conftest.py
  unit/                # test_guardrails.py, test_retrieval.py, test_helpers.py, test_tools.py
  property/            # test_invariants.py (Hypothesis)
  component/           # test_orchestrator.py (mocked OpenAI)
  integration/         # test_agent_flow.py (real DB + docs, mocked OpenAI)
evals/
  promptfoo.yaml       # scenario evals (includes cases from promptfoo_cases.yaml inline)
  prompt.txt           agent_provider.py    run_agent.py
trt_adapters/          # Trajectly adapter scripts (invoice_lookup, mfa_reset, enterprise_escalation)
trajectly/
  config.yaml
  specs/               # invoice_lookup.agent.yaml, mfa_reset_requires_approval.agent.yaml,
                       # enterprise_sensitive_escalation.agent.yaml
  cases/               # human-readable scenario definitions (mirror specs contracts)
.github/workflows/
  ci.yaml
```

## Setup

**Prerequisites:** Python 3.11+, [Node.js/npx](https://nodejs.org) (for promptfoo evals only).

```bash
python3.11 -m venv .venv
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
cp .env.example .env             # add your OPENAI_API_KEY (loaded automatically)
make init-db                     # create SQLite DB from fixtures
```

To regenerate fixture data from scratch: `make generate-data && make init-db`.
Data files in `data/generated/` are checked in so you can run tests immediately after cloning.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(none)* | Required for running the agent and live evals. |
| `SUPPORT_DB_PATH` | `./data/support.db` | SQLite database path. |
| `SUPPORT_DOCS_PATH` | `./data/docs` | Documentation corpus path. |

## SQLite schema

Defined in `app/schema.sql`. Four tables:

| Table | Columns |
|-------|---------|
| `accounts` | id, name, tier, is_enterprise |
| `subscriptions` | account_id, plan, status |
| `invoices` | id, account_id, amount_cents, status, note |
| `tickets` | id, account_id, subject, status |

Initialize with `make init-db` or `python scripts/init_db.py`.

## Run the agent

```bash
make run QUERY="Why was invoice INV-1007 higher this month?"
python -m app.main --query "What plan is account ACME-001 on?"
python -m app.main --query "Can you reset MFA for the admin on account ACME-ENT-09?"
python -m app.main --query "Please escalate ticket TICK-2041"
```

## Tests and evals

| Layer | Command | What it tests |
|-------|---------|---------------|
| **Unit** | `make test-unit` | Guardrails, retrieval, helpers |
| **Property** | `make test-property` | Hypothesis invariants (normalization, sanitization) |
| **Component** | `make test-component` | Orchestrator with mocked model |
| **Integration** | `make test-integration` | Full flow: real DB + docs, mocked OpenAI |
| **All pytest** | `make test` | All of the above |
| **Promptfoo** | `make eval-promptfoo` | Scenario evals: refusal, groundedness, escalation |
| **Garak** | `make eval-garak` | Adversarial/safety probes |
| **Trajectly record** | `make trajectly-record` | Record golden baselines (needs API key) |
| **Trajectly run** | `make trajectly-run` | Trajectory regression against baselines |
| **Lint** | `make lint` | Ruff checks on app, tests, scripts |

## CI pipeline

See `.github/workflows/ci.yaml`. Two tiers:

**Always run (no API key needed, blocking):**
- Lint, unit tests, property tests, component tests, integration tests

**Only when `OPENAI_API_KEY` secret is configured (informational):**
- Trajectly smoke (one spec via `trajectly/trajectly-action`)
- Promptfoo evals (main branch)
- Garak smoke (main branch)

To enable the API-dependent jobs in your fork: go to **Settings > Secrets and variables > Actions**, add a secret named `OPENAI_API_KEY` with your key. Jobs are silently skipped when the secret is not set.

## Testing pyramid

| Layer | Catches | Misses | Blocks |
|-------|---------|--------|--------|
| Unit (pytest) | Policy, auth, retrieval filters, helpers | Integration, LLM behavior | PR + release |
| Property (Hypothesis) | Invariants, normalization, sanitization | Concrete scenarios | PR + release |
| Component (pytest + mocks) | Orchestrator branches, tool selection | Full stack, real model | PR |
| Integration (pytest) | E2E flows, refusal/escalation paths | Non-deterministic LLM output | PR + release |
| Trajectly | Tool-call sequence regression, contracts | Semantic quality, safety | PR (smoke), main (full) |
| Promptfoo | Scenario quality, refusal, groundedness | Execution path, determinism | Main + release |
| Garak | Adversarial/safety (injection, override) | Business logic, trajectory | Main (smoke) |

**Trajectly catches execution-path regressions, but it does not replace scenario evals, safety testing, or broad behavioral assessment.** It is one layer in the pyramid.

## Blog

For a deep dive into the testing strategy, see [blog/testing-the-support-agent.md](blog/testing-the-support-agent.md).
