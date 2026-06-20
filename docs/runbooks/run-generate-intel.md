# Runbook: Generate a brief

## Setup (one-time)

**1. Clone and enter the project**

```bash
git clone <repo-url>
cd competitive-intel-agent
```

**2. Create a virtual environment and install dependencies**

With `uv` (recommended):

```bash
uv sync
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

Or with plain pip:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

**3. Set your API keys**

```bash
cp .env.template .env
```

Open `.env` and fill in:

```
TAVILY_API_KEY="tvly-..."          # required — https://app.tavily.com
ANTHROPIC_API_KEY="sk-ant-..."     # primary LLM — https://console.anthropic.com
# OPENAI_API_KEY="sk-..."          # fallback LLM (either/or)
LOGFIRE_TOKEN="pylf_..."           # optional — https://logfire.pydantic.dev
```

Requires Python 3.11+.

## Run

```bash
.venv/bin/competitive-intel brief "Perplexity" --focus funding,product --window month
```

If `competitive-intel` is on your PATH (activated venv or `uv run`):

```bash
competitive-intel brief "Perplexity" --focus funding,product --window month
```

The module form is always equivalent if you prefer it:

```bash
.venv/bin/python -m competitive_intel brief "Perplexity" --focus funding,product --window month
```

## Options

| Option | Values | Default |
|---|---|---|
| `COMPANY` (positional, required) | any company name | — |
| `--focus` | comma-separated: `funding,financials,product,pricing,hiring,partnerships,market_positioning,risk` | all |
| `--window` | `day` `week` `month` `year` | `month` |
| `--provider` | `anthropic` `openai` | from env |
| `--out` | file path | print to stdout |

## What you get

A markdown brief (see [`examples/sample_brief.md`](../../examples/sample_brief.md)) plus a run-summary panel: provider/model, sources cited, findings kept/dropped, **citation coverage %**, self-correction retries, duration, and token usage.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Missing TAVILY_API_KEY` | Set it in `.env`. |
| `No model provider key found` | Set `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. |
| `ModuleNotFoundError: No module named 'competitive_intel'` | The `.venv` is corrupted — usually from being copied or synced (e.g. iCloud/Dropbox sync a venv living under `~/Documents`). Venvs are not relocatable. Recreate it: `rm -rf .venv && uv sync`. As a one-off escape hatch you can also run `PYTHONPATH=src .venv/bin/python -m competitive_intel brief …`. |
| 0 sources, "evidence does not mention X" | Run summary shows sources=0 but the brief ran. Try `--window year` or run without `--focus` to let all categories attempt retrieval. |
| Few/zero findings | The window may be too narrow — try `--window year`; low-evidence categories already auto-retry once. |
| Low coverage % | Verification dropped findings with unresolvable citations — that's the safety net working. |

---

# Runbook: Read the Logfire trace

## Enable tracing

Set `LOGFIRE_TOKEN` in `.env` (get one at <https://logfire.pydantic.dev>). Without it, tracing is a silent no-op and the CLI still works.

Configuration happens once in `observability.py`:

```16:62:src/competitive_intel/observability/__init__.py
def configure(settings: Settings | None = None) -> bool:
    """Configure Logfire + instrumentation once. Returns True if tracing is live."""
```

## What a run looks like

Run any brief, then open the project in the Logfire UI. One brief = one trace:

```
brief (company=Perplexity, recency_window=month)
├─ retrieve_rerank (n_plan_items=2)
│  ├─ httpx POST api.tavily.com/search        ← instrument_httpx / requests
│  └─ httpx POST api.tavily.com/extract
├─ ledger
│  └─ info "retrieval"  {category, query, n_results, n_passages,
│                        max_fused_score, mean_fused_score, retried, top_k_ids}
├─ synthesize (provider=anthropic, model=claude-sonnet-4-5)
│  └─ ChatAnthropic ...                        ← OpenInference LangChain spans
├─ verify
└─ info "run_summary"  {n_sources, n_findings, n_dropped,
                        citation_coverage, retries, duration_s, *_tokens}
```

## How the attributes get there

Every stage is wrapped in a span and every typed artifact is logged as structured attributes:

```65:79:src/competitive_intel/observability/__init__.py
@contextmanager
def span(name: str, **attributes: Any):
    """Open a Logfire span for a pipeline stage (no-op if tracing is off)."""
    if _logfire is not None:
        with _logfire.span(name, **attributes) as current:
            yield current
    else:
        yield None


def log_model(message: str, model: BaseModel) -> None:
    """Log a typed pipeline artifact as structured attributes."""
    if _logfire is not None:
        _logfire.info(message, **model.model_dump())
```

## What to look for (demo)

- **`retrieval` events** — `max_fused_score` and `retried=true` show the self-correction loop firing on thin categories.
- **`synthesize` span** — the single grounded model call and its token usage.
- **`run_summary`** — `citation_coverage` and `n_dropped` prove the verification gate ran.
- **Tavily HTTP spans** — concrete evidence the brief used live web data.
