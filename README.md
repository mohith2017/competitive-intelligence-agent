# Competitive Intelligence Agent

Source-verified competitive intelligence briefs for **finance, investment-research, and corporate-development** teams, powered by [Tavily](https://tavily.com) + LangChain.

Give it a company; get back a structured, **cited** markdown brief built from **live web data** — with every claim traceable to a numbered source and a full **Logfire/OpenTelemetry** trace of how it was produced.

```bash
competitive-intel brief "Perplexity" --focus funding,product --window month
```

## Why it's different from the starter

The starter agent does one untuned web search and writes a paragraph. This does a **Hybrid RAG** pipeline — *Tavily Evidence Fusion*:

`plan → retrieve (Tavily advanced + extract) → rerank (BM25 + Tavily via RRF) → evidence ledger [S#] → synthesize (grounded) → verify (deterministic citations)`

Result: recent, ranked, cited, and auditable — the three things plain LLMs cannot give a diligence team.

### Sample output

```
$ competitive-intel brief "Anthropic" --focus funding,product,hiring --window month

## Executive summary
Anthropic's last-month funding signal is highly material: reports dated May 28, 2026 say
the company raised $65B at a $965B valuation, putting it near a $1T valuation mark [S10, S5, S1].
Product cadence also appears rapid, with Anthropic launching Claude Opus 4.8 on May 28, releasing
Claude Fable 5 publicly on June 9, and announcing a Claude Code Artifacts update for enterprise
live dashboards and workspaces on June 18 [S8, S12, S2].

## Findings
### Funding
- Anthropic reportedly raised $65B at a $965B valuation, bringing its valuation near $1T. (as of 2026-05-28) [S10] [S5] [S1]
- Bloomberg reported that Anthropic was expected to close an over-$30B funding round as soon as the following week. (as of 2026-05-22) [S9]

### Product
- Anthropic launched Claude Opus 4.8 on May 28, 2026. (as of 2026-05-28) [S8]
- Anthropic released the Claude Fable 5 AI model to the public on June 9, 2026. (as of 2026-06-09) [S12]
- Anthropic announced a Claude Code Artifacts update with live, shared dashboards for enterprise users. (as of 2026-06-18) [S2]

### Hiring
- Anthropic acquired developer-tooling startup Stainless during the week of May 18, 2026. (as of 2026-05-22) [S7]

╭─────────────────────────── Run summary ───────────────────────────╮
│ Provider / model           openai / gpt-5.5                       │
│ Sources cited              9                                      │
│ Findings (kept / dropped)  9 / 0                                  │
│ Citation coverage          100%                                   │
│ Self-correction retries    0                                      │
│ Duration                   24.94s                                 │
│ Tokens (in / out)          4725 / 1704                            │
╰───────────────────────────────────────────────────────────────────╯
```

### Sample Logfire trace

Every run produces a full OpenTelemetry trace in Logfire showing retrieval, rerank, synthesis, and verification as nested spans — with Tavily HTTP calls and LLM calls auto-instrumented.

The full span tree: `brief → retrieve_rerank → retrieve (×N) → tavily_search / tavily_extract → ledger → synthesize → verify → run_summary`

Logfire trace — tree with timing

The `synthesize` span shows the LangChain `RunnableParallel` internals and the parsed `DraftBrief` with every structured finding and citation:

Logfire trace — synthesize span with parsed DraftBrief

The `tavily_extract` span shows the raw full-page content fetched from each URL before reranking:

Logfire trace — tavily_extract span with raw content

## Deliverables


| Deliverable                                                                                            | Location                                                                                               |
| ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------ |
| **Technical statement** — approach, thought process, and business value                                | `[docs/technical-statement.md](docs/technical-statement.md)`                                           |
| **Explainer** — deep-dive on Evidence Fusion, grounded synthesis, observability, and context isolation | `[docs/explainer/explainer-summary.md](docs/explainer/explainer-summary.md)`                           |
| **Build record** — coding agent session log (Cursor)                                                   | `[docs/explainer/explainer-coding-agent-summary.md](docs/explainer/explainer-coding-agent-summary.md)` |
| **Build log** — what was built and why, in plain language                                              | `[docs/explainer/explainer-build-log.md](docs/explainer/explainer-build-log.md)`                       |
| **Sample output** — example brief for Perplexity                                                       | `[examples/sample_brief.md](examples/sample_brief.md)`                                                 |


## Quickstart

Requires `TAVILY_API_KEY` + `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. See `[docs/runbooks/run-generate-intel.md](docs/runbooks/run-generate-intel.md)` for where to get them.

For Logfire observability/tracing setup: `[docs/runbooks/run-generate-intel.md#enable-tracing](docs/runbooks/run-generate-intel.md#enable-tracing)`

```bash
cp .env.template .env                    # fill in your API keys
uv sync                                  # creates .venv and installs deps
source .venv/bin/activate                # Windows: .venv\Scripts\activate
competitive-intel brief "Anthropic" --focus funding,product,hiring --window month
competitive-intel eval --cases eval/cases.yaml
```

## Learn more

- Architecture + module map: `[docs/explainer/explainer-summary.md#architecture](docs/explainer/explainer-summary.md#architecture)`
- Runbooks (generate a brief, read traces, run evals): `[docs/runbooks/](docs/runbooks)`

Requires Python 3.11+.