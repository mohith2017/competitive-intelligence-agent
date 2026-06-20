from __future__ import annotations

import json
import os
from typing import Any

from langchain_tavily import TavilyExtract, TavilySearch

from ..config import Settings, get_settings
from ..models import Category, SearchResult


def _as_dict(raw: Any) -> dict[str, Any]:
    """Tavily tools may return a dict or a JSON string depending on version."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"results": parsed}
        except json.JSONDecodeError:
            return {}
    return {}


def results_from_payload(
    payload: dict[str, Any], category: Category | None
) -> list[SearchResult]:
    """Normalize a Tavily search payload (LangChain tool or MCP) into SearchResults."""
    results: list[SearchResult] = []
    for item in payload.get("results", []) or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        results.append(
            SearchResult(
                url=item.get("url", ""),
                title=item.get("title") or "Untitled",
                content=item.get("content") or "",
                raw_content=item.get("raw_content"),
                score=float(item.get("score") or 0.0),
                published_date=item.get("published_date"),
                category=category,
            )
        )
    return results


def extracted_from_payload(payload: dict[str, Any]) -> dict[str, str]:
    """Normalize a Tavily extract payload into ``{url: full_text}``."""
    out: dict[str, str] = {}
    for item in payload.get("results", []) or []:
        if isinstance(item, dict) and item.get("url"):
            text = item.get("raw_content") or item.get("content") or ""
            if text:
                out[item["url"]] = text
    return out


class TavilyRetriever:
    """Live web retrieval layer built on Tavily."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.tavily_api_key:
            os.environ.setdefault("TAVILY_API_KEY", self.settings.tavily_api_key)

    _FINANCE_TOPIC_CATEGORIES: frozenset[Category] = frozenset({"financials", "funding"})

    def search(
        self,
        query: str,
        *,
        category: Category | None = None,
        topic: str | None = None,
        time_range: str | None = None,
        search_depth: str = "advanced",
        max_results: int | None = None,
        include_domains: list[str] | None = None,
    ) -> list[SearchResult]:
        """
        Run one advanced Tavily search and normalize the results.
        """
        if topic is None:
            topic = "finance" if category in self._FINANCE_TOPIC_CATEGORIES else "general"
        tool = TavilySearch(
            max_results=max_results or self.settings.results_per_query,
            search_depth=search_depth,
            topic=topic,
            time_range=time_range or self.settings.default_recency_window,
            include_raw_content=True,
            include_domains=include_domains or [],
        )
        payload = _as_dict(tool.invoke({"query": query}))
        return results_from_payload(payload, category)

    def extract(self, urls: list[str], *, extract_depth: str = "advanced") -> dict[str, str]:
        """Fetch full page text for ``urls``; returns ``{url: raw_content}``."""
        urls = [u for u in dict.fromkeys(urls) if u]  # dedupe, keep order
        if not urls:
            return {}
        tool = TavilyExtract(extract_depth=extract_depth)
        payload = _as_dict(tool.invoke({"urls": urls}))
        return extracted_from_payload(payload)
