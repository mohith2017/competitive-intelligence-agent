"""Render a verified ``Brief`` to markdown matching examples/sample_brief.md."""

from __future__ import annotations

from ..models import Brief, Category

CATEGORY_LABELS: dict[Category, str] = {
    "funding": "Funding",
    "financials": "Financials",
    "product": "Product",
    "pricing": "Pricing",
    "hiring": "Hiring",
    "partnerships": "Partnerships",
    "market_positioning": "Market Positioning",
    "risk": "Risk",
}


def _citation_tags(ids: list[str]) -> str:
    return " ".join(f"[{cid}]" for cid in ids)


def render_markdown(brief: Brief) -> str:
    supported = len(brief.findings)
    total = supported + len(brief.dropped_findings)
    coverage_pct = round(brief.citation_coverage * 100)

    lines: list[str] = [
        f"# Competitive Intelligence Brief: {brief.company}",
        "",
        (
            f"_Generated {brief.generated_at} | recency window: last "
            f"{brief.recency_window} | citation coverage: {coverage_pct}% "
            f"({supported}/{total} findings supported)_"
        ),
        "",
        "## Executive summary",
        "",
        brief.executive_summary or "_No grounded summary could be produced._",
        "",
        "## Findings",
    ]

    # Order categories by focus areas, then any remaining categories present.
    present = [f.category for f in brief.findings]
    ordered: list[Category] = []
    for cat in [*brief.focus_areas, *present]:
        if cat in present and cat not in ordered:
            ordered.append(cat)

    if not brief.findings:
        lines += ["", "_No source-verified findings for this window._"]

    for category in ordered:
        items = [f for f in brief.findings if f.category == category]
        if not items:
            continue
        lines += ["", f"### {CATEGORY_LABELS.get(category, category.title())}"]
        for finding in items:
            as_of = f" (as of {finding.as_of})" if finding.as_of else ""
            tags = _citation_tags(finding.citation_ids)
            tail = f" {tags}" if tags else ""
            lines.append(f"- [{finding.confidence}] {finding.claim}{as_of}{tail}")

    lines += ["", "## Sources", ""]
    if brief.sources:
        for src in brief.sources:
            date = f" ({src.published_date})" if src.published_date else ""
            lines.append(f"- **[{src.id}]** {src.title}{date} — {src.url}")
    else:
        lines.append("_No sources cited._")

    return "\n".join(lines) + "\n"
