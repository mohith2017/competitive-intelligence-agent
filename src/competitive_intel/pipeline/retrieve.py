"""
Retrieval: execute the plan against Tavily and enrich top hits with full-text
extraction.
"""

from __future__ import annotations

from ..config import Settings
from ..models import Category, SearchResult
from ..tools import TavilyRetriever
from .plan import PlanItem


def retrieve_for_item(
    item: PlanItem,
    retriever: TavilyRetriever,
    settings: Settings,
    time_range: str,
) -> list[SearchResult]:
    """Search one plan item and attach extracted full text to the top URLs."""
    results = retriever.search(
        item.query,
        category=item.category,
        time_range=time_range,
        search_depth="advanced",
        max_results=settings.results_per_query,
    )
    if not results:
        return []

    ranked = sorted(results, key=lambda r: r.score, reverse=True)
    to_extract = [r.url for r in ranked[: settings.extract_top_n] if not r.raw_content]
    if to_extract:
        extracted = retriever.extract(to_extract)
        for result in results:
            if result.url in extracted:
                result.raw_content = extracted[result.url]
    return results


def retrieve_plan(
    plan: list[PlanItem],
    retriever: TavilyRetriever,
    settings: Settings,
    time_range: str,
) -> dict[Category, list[SearchResult]]:
    """Run the full plan, returning results grouped by category."""
    by_category: dict[Category, list[SearchResult]] = {}
    for item in plan:
        results = retrieve_for_item(item, retriever, settings, time_range)
        by_category.setdefault(item.category, []).extend(results)
    return by_category
