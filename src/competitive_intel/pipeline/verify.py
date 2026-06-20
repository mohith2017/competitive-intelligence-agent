"""Deterministic verification (aggregation step)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from ..models import Brief, Category, Citation, DraftBrief, EvidenceLedger, Finding

_ID_RE = re.compile(r"[sS]?0*(\d+)")

_WINDOW_DAYS = {"day": 1, "week": 7, "month": 31, "year": 366}


def normalize_citation_id(raw: str) -> str | None:
    """Coerce 'S1', 's01', '[S1]', '1' -> 'S1'; return None if not parseable."""
    if not isinstance(raw, str):
        return None
    match = _ID_RE.search(raw.strip())
    return f"S{int(match.group(1))}" if match else None


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(value[: len(fmt) + 2], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value.replace("Z", "")).date()
    except ValueError:
        return None


def verify(
    draft: DraftBrief,
    ledger: EvidenceLedger,
    *,
    company: str,
    recency_window: str,
    focus_areas: list[Category],
    generated_at: str | None = None,
) -> Brief:
    """Resolve citations, drop unsupported findings, and build the final brief."""
    valid_ids = set(ledger.citation_map().keys())
    citation_by_id = ledger.citation_map()

    kept: list[Finding] = []
    dropped: list[Finding] = []
    cited_ids: list[str] = []

    for finding in draft.findings:
        resolved: list[str] = []
        for raw in finding.citation_ids:
            cid = normalize_citation_id(raw)
            if cid and cid in valid_ids and cid not in resolved:
                resolved.append(cid)
        clean = finding.model_copy(update={"citation_ids": resolved})
        if resolved:
            kept.append(clean)
            for cid in resolved:
                if cid not in cited_ids:
                    cited_ids.append(cid)
        else:
            dropped.append(clean)

    total = len(draft.findings)
    coverage = round(len(kept) / total, 3) if total else 0.0

    sources = sorted(
        (citation_by_id[c] for c in cited_ids),
        key=lambda c: int(c.id[1:]),
    )

    return Brief(
        company=company,
        generated_at=generated_at or date.today().isoformat(),
        recency_window=recency_window,
        focus_areas=focus_areas,
        executive_summary=draft.executive_summary.strip(),
        findings=kept,
        sources=sources,
        citation_coverage=coverage,
        dropped_findings=dropped,
    )


def recency_adherence(
    sources: list[Citation], window: str, *, today: date | None = None
) -> float:
    """
    Fraction of dated sources that fall within the recency window.
    """
    today = today or date.today()
    horizon = _WINDOW_DAYS.get(window, 31)
    cutoff = today - timedelta(days=horizon)
    dated = [d for d in (_parse_date(c.published_date) for c in sources) if d]
    if not dated:
        return 1.0
    within = sum(1 for d in dated if d >= cutoff)
    return round(within / len(dated), 3)
