from __future__ import annotations

from ..models import Category, Citation, EvidenceLedger, Passage


def build_ledger(passages_by_category: dict[Category, list[Passage]]) -> EvidenceLedger:
    """Flatten per-category passages into a deduped, citable ledger."""
    all_passages: list[Passage] = []
    for passages in passages_by_category.values():
        all_passages.extend(passages)

    best_score: dict[str, float] = {}
    meta: dict[str, Passage] = {}
    for passage in all_passages:
        if passage.url not in best_score or passage.fused_score > best_score[passage.url]:
            best_score[passage.url] = passage.fused_score
            meta[passage.url] = passage

    ordered_urls = sorted(best_score, key=lambda u: best_score[u], reverse=True)
    citations: list[Citation] = []
    for i, url in enumerate(ordered_urls, start=1):
        src = meta[url]
        citations.append(
            Citation(
                id=f"S{i}",
                title=src.title,
                url=url,
                published_date=src.published_date,
            )
        )

    url_to_id = {c.url: c.id for c in citations}
    all_passages.sort(
        key=lambda p: (int(url_to_id[p.url][1:]), p.category or "", -p.fused_score)
    )
    return EvidenceLedger(passages=all_passages, citations=citations)
