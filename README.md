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

## Quickstart

```bash
cp .env.template .env                    # add TAVILY_API_KEY + ANTHROPIC_API_KEY (or OPENAI_API_KEY)
uv sync                                  # creates .venv and installs deps
source .venv/bin/activate                # Windows: .venv\Scripts\activate
competitive-intel brief "Anthropic" --focus funding,product,hiring --window month
competitive-intel eval --cases eval/cases.yaml
```

## Learn more

- Approach, audience, and value: [`docs/technical-statement.md`](docs/technical-statement.md)
- Architecture + module map: [`docs/explainer/explainer-summary.md`](docs/explainer/explainer-summary.md#architecture)
- Runbooks (run a brief, read traces, run evals): [`docs/runbooks/`](docs/runbooks)
- The explainer (deep-research context engineering): [`docs/explainer/`](docs/explainer)
- How this was built: [`docs/explainer/explainer-build-log.md`](docs/explainer/explainer-build-log.md)
- Sample output: [`examples/sample_brief.md`](examples/sample_brief.md)

Requires Python 3.11+.
