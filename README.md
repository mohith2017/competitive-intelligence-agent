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

## Deliverables

| Deliverable | Location |
|---|---|
| **Technical statement** — approach, thought process, and business value | [`docs/technical-statement.md`](docs/technical-statement.md) |
| **Explainer** — deep-dive on Evidence Fusion, grounded synthesis, observability, and context isolation | [`docs/explainer/explainer-summary.md`](docs/explainer/explainer-summary.md) |
| **Build record** — coding agent session log (Cursor) | [`docs/explainer/explainer-coding-agent-summary.md`](docs/explainer/explainer-coding-agent-summary.md) |
| **Build log** — what was built and why, in plain language | [`docs/explainer/explainer-build-log.md`](docs/explainer/explainer-build-log.md) |
| **Sample output** — example brief for Perplexity | [`examples/sample_brief.md`](examples/sample_brief.md) |

## Quickstart

Requires `TAVILY_API_KEY` + `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`. See [`docs/runbooks/run-generate-intel.md`](docs/runbooks/run-generate-intel.md) for where to get them.

```bash
cp .env.template .env                    # fill in your API keys
uv sync                                  # creates .venv and installs deps
source .venv/bin/activate                # Windows: .venv\Scripts\activate
competitive-intel brief "Anthropic" --focus funding,product,hiring --window month
competitive-intel eval --cases eval/cases.yaml
```

## Learn more

- Architecture + module map: [`docs/explainer/explainer-summary.md#architecture`](docs/explainer/explainer-summary.md#architecture)
- Runbooks (generate a brief, read traces, run evals): [`docs/runbooks/`](docs/runbooks)

Requires Python 3.11+.
