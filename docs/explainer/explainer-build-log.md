# Build log

This was built AI-assisted. This log records the decisions made *after* reviewing the agent's output — what was kept, what was rejected, and why — plus the notable course-corrections during the build.

## Key decisions

### 1. Pipeline, not `create_agent` / ReAct loop
**Decision:** keep retrieval deterministic and make synthesis a single `with_structured_output` call.
**Rejected:** a `create_agent` + ToolStrategy loop where the model decides when to search.
**Why:** for diligence, precision and verifiability matter more than autonomy. A deterministic retrieval half + one bounded LLM call + a deterministic verify half is cheaper, reproducible, fully testable, and produces a clean trace. `create_agent` is the right tool when the model must interleave tool calls and structured output — not here. (Noted as future "research mode".)

### 2. Reciprocal Rank Fusion, not a weighted score blend
**Decision:** fuse the Tavily *rank* and the BM25 *rank* with RRF.
**Rejected:** `alpha * tavily_score + (1-alpha) * bm25_score`.
**Why:** the two scores live on different, unstable scales (Tavily 0–1 semantic; BM25 unbounded and corpus-dependent). Blending raw scores needs constant retuning; fusing ranks is scale-free and robust. This was reinforced by a test surprise — see course-corrections.

### 3. Verification *drops* unsupported findings (doesn't just flag them)
**Decision:** if a finding's citations don't resolve to the ledger, remove it and report it under `dropped_findings`; surface `citation_coverage`.
**Rejected:** keeping all findings and annotating confidence only.
**Why:** the product promise is "everything in the brief is source-backed." A flagged-but-present hallucination still ends up in someone's memo. Dropping is the honest default; coverage % makes the trade-off visible.

### 4. Module context isolation, not hierarchical subagents
**Decision:** split responsibilities into typed modules (`tools/`, `pipeline/`, `synthesize.py`, `verify.py`).
**Rejected:** a multi-subagent (planner/executor) orchestration.
**Why:** subagents add coordination overhead and more non-determinism for the same separation-of-concerns benefit. Typed module boundaries give isolation *and* unit-testability. Documented in [explainer ch.05](explainer-summary.md#05--context-isolation-subagents-simpler-to-verify).

### 5. Deterministic eval, not LLM-as-judge / DeepEval
**Decision:** score coverage, source validity, recency adherence — all computable without a model.
**Rejected:** DeepEval / an LLM judge.
**Why:** the trust question here is concrete ("does every claim resolve to a real, recent source?"), so a second model's opinion adds cost and variance without adding signal. Metric functions are unit-tested offline.

## Course-corrections during the build

- **`uv` not on PATH → used the venv's `pip`.** Installed deps and the editable package via `./.venv/bin/python -m pip` instead of `uv`.
- **Editable `.pth` not honored in this venv.** The `uv`-created venv on a path containing spaces (`Tavily Take home`) didn't load the editable `.pth`, so `import competitive_intel` failed even though the package was correct (manual `src` insert worked). Fix: set `pytest` `pythonpath = ["src"]` and added `__main__.py` so `python -m competitive_intel` always works; documented `PYTHONPATH=src` as the fallback run form. In a normal-path environment `uv sync` + the console script work as-is.
- **BM25 IDF collapses on a 2-doc corpus.** A fusion test asserted BM25 would rank the on-topic doc higher with 2 documents; it didn't, because BM25 IDF is 0 when a term appears in 1 of 2 docs. Rewrote the test to use a ≥3-doc corpus (realistic) and to assert defensible properties (lexical layer scores on-topic text higher; fusion ranks the well-scored on-topic passage first).
- **Removed all Nebius references** from the starting point; provider strategy is Claude-primary, OpenAI-fallback only.

## Verification gates

- [ ] `competitive-intel brief "Perplexity" --focus funding,product --window month` produces a brief with resolvable `[S#]` citations. *(Requires live keys in `.env`.)*
- [ ] Logfire trace shows plan → retrieve → rerank → synthesize → verify spans. *(Requires `LOGFIRE_TOKEN`.)*
- [x] Explainer code blocks reference real `src/` modules and functions.
- [x] `pytest` green: 13 deterministic tests across the RAG agent and evals/observability.
- [x] No unverified generic-RAG essay — every explainer section ties to this repo.
- [~] `--via-mcp` stretch: wired against the verified `langchain-mcp-adapters` API (`MultiServerMCPClient.get_tools()` + async `ainvoke`); shared normalizers unit-tested. Live MCP round-trip not verified at build time (no key/network).
