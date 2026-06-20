"""
Evidence Fusion rerank: combine Tavily relevance with lexical BM25 via
Reciprocal Rank Fusion (RRF).
"""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

from ..config import Settings
from ..models import Passage, SearchResult

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) > 1]


def _compact(text: str, cap: int) -> str:
    """Collapse whitespace and cap length for a token-efficient ledger entry."""
    collapsed = " ".join(text.split())
    if len(collapsed) <= cap:
        return collapsed
    return collapsed[:cap].rsplit(" ", 1)[0] + "..."


def _ranks(scores: list[float]) -> dict[int, int]:
    """Map item index -> 1-based rank (highest score = rank 1)."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return {idx: rank for rank, idx in enumerate(order, start=1)}


def fuse_category(
    query: str,
    results: list[SearchResult],
    settings: Settings,
) -> list[Passage]:
    """Rank one category's results by RRF(Tavily, BM25) and return top-K passages."""
    if not results:
        return []

    texts = [r.best_text() or r.title for r in results]
    tokenized = [_tokenize(t) for t in texts]
    bm25 = BM25Okapi(tokenized) if any(tokenized) else None
    bm25_scores = (
        list(bm25.get_scores(_tokenize(query))) if bm25 else [0.0] * len(results)
    )

    tavily_ranks = _ranks([r.score for r in results])
    bm25_ranks = _ranks(bm25_scores)
    k = settings.rrf_k

    passages: list[Passage] = []
    for i, result in enumerate(results):
        fused = 1.0 / (k + tavily_ranks[i]) + 1.0 / (k + bm25_ranks[i])
        passages.append(
            Passage(
                url=result.url,
                title=result.title,
                text=_compact(result.best_text() or result.title, settings.passage_char_cap),
                published_date=result.published_date,
                category=result.category,
                tavily_score=result.score,
                bm25_score=float(bm25_scores[i]),
                fused_score=fused,
            )
        )

    passages.sort(key=lambda p: p.fused_score, reverse=True)
    return passages[: settings.top_k_per_category]
