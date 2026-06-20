from __future__ import annotations

import time
from datetime import date

from ..config import Settings, get_settings
from ..models import (
    Brief,
    Category,
    EvidenceLedger,
    Passage,
    RetrievalSpanMeta,
    RunSummary,
    SearchResult,
)
from ..observability import configure, log_model, span
from .synthesize import synthesize
from ..tools import TavilyRetriever
from .verify import verify
from .ledger import build_ledger
from .plan import PlanItem, build_plan, refine_query
from .rerank import fuse_category
from .retrieve import retrieve_for_item


def _fused_stats(passages: list[Passage]) -> tuple[float, float]:
    if not passages:
        return 0.0, 0.0
    scores = [p.fused_score for p in passages]
    return max(scores), sum(scores) / len(scores)


def _retrieve_and_rank_category(
    category: Category,
    items: list[PlanItem],
    retriever: TavilyRetriever,
    settings: Settings,
    company: str,
    recency_window: str,
) -> tuple[list[Passage], RetrievalSpanMeta]:
    """Retrieve + fuse one category, with a single self-correction retry."""
    query = items[0].query if items else category
    results: list[SearchResult] = []
    for item in items:
        results.extend(retrieve_for_item(item, retriever, settings, recency_window))

    passages = fuse_category(query, results, settings)
    max_fused, mean_fused = _fused_stats(passages)
    retried = False

    if items and (not passages or max_fused < settings.min_fused_score):
        retried = True
        refined = refine_query(items[0], company)
        results.extend(retrieve_for_item(refined, retriever, settings, recency_window))
        passages = fuse_category(refined.query, results, settings)
        max_fused, mean_fused = _fused_stats(passages)
        query = refined.query

    meta = RetrievalSpanMeta(
        stage="retrieve_rerank",
        category=category,
        query=query,
        n_results=len(results),
        n_passages=len(passages),
        max_fused_score=round(max_fused, 5),
        mean_fused_score=round(mean_fused, 5),
        retried=retried,
    )
    return passages, meta


def run_brief(
    company: str,
    focus_areas: list[Category] | None = None,
    recency_window: str | None = None,
    settings: Settings | None = None,
    model=None,
    retriever=None,
    configure_observability: bool = True,
) -> tuple[Brief, RunSummary]:
    """Produce a verified competitive intelligence brief and a run summary."""
    settings = settings or get_settings()
    focus_areas = focus_areas or settings.default_categories
    recency_window = recency_window or settings.default_recency_window
    if configure_observability:
        configure(settings)

    provider = settings.resolve_provider()
    model_name = settings.model_name(provider)
    started = time.perf_counter()

    with span("brief", company=company, recency_window=recency_window):
        retriever = retriever or TavilyRetriever(settings)
        plan = build_plan(company, focus_areas)

        passages_by_category: dict[Category, list[Passage]] = {}
        metas: list[RetrievalSpanMeta] = []
        retries = 0

        with span("retrieve_rerank", n_plan_items=len(plan)):
            for category in focus_areas:
                items = [p for p in plan if p.category == category]
                passages, meta = _retrieve_and_rank_category(
                    category, items, retriever, settings, company, recency_window
                )
                passages_by_category[category] = passages
                metas.append(meta)
                if meta.retried:
                    retries += 1

        with span("ledger"):
            ledger: EvidenceLedger = build_ledger(passages_by_category)
            url_to_id = ledger.url_to_id()
            for meta in metas:
                cat_passages = passages_by_category.get(meta.category or "", [])
                meta.top_k_ids = [
                    url_to_id[p.url] for p in cat_passages if p.url in url_to_id
                ]
                log_model("retrieval", meta)

        with span("synthesize", provider=provider, model=model_name):
            synth = synthesize(
                company, focus_areas, recency_window, ledger, settings, model
            )

        with span("verify"):
            brief = verify(
                synth.draft,
                ledger,
                company=company,
                recency_window=recency_window,
                focus_areas=focus_areas,
                generated_at=date.today().isoformat(),
            )

        summary = RunSummary(
            company=company,
            recency_window=recency_window,
            focus_areas=focus_areas,
            provider=provider,
            model=model_name,
            n_sources=len(brief.sources),
            n_findings=len(brief.findings),
            n_dropped=len(brief.dropped_findings),
            citation_coverage=brief.citation_coverage,
            retries=retries,
            duration_s=round(time.perf_counter() - started, 2),
            prompt_tokens=synth.prompt_tokens,
            completion_tokens=synth.completion_tokens,
        )
        log_model("run_summary", summary)

    return brief, summary
