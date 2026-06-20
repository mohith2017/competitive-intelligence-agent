"""Grounded synthesis (aggregation step)."""

from __future__ import annotations

from dataclasses import dataclass

from ..config import Settings, build_model, get_settings
from ..models import Category, DraftBrief, EvidenceLedger

SYNTHESIS_SYSTEM = """You are a competitive-intelligence analyst writing for finance, \
investment-research, and corporate-development teams doing company diligence.

Rules:
- Use ONLY the numbered evidence provided. Do not use prior knowledge.
- Every finding MUST cite one or more source ids exactly as given (e.g. ["S1", "S3"]).
- Do not invent sources or ids. If the evidence does not support a claim, omit it.
- Each finding is ONE specific, factual statement (amounts, dates, names where possible).
- Set confidence: "high" if multiple/primary sources agree, "med" if one solid source, \
"low" if indirect or weak.
- Set as_of to the date the fact was true (prefer YYYY-MM-DD from the evidence).
- Group findings by the provided categories. Prefer recent, material facts.
- The executive_summary is 3-5 sentences a busy analyst could paste into a memo."""


@dataclass
class SynthesisResult:
    draft: DraftBrief
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def _usage(raw) -> tuple[int | None, int | None]:
    usage = getattr(raw, "usage_metadata", None) or {}
    if isinstance(usage, dict):
        return usage.get("input_tokens"), usage.get("output_tokens")
    return None, None


def synthesize(
    company: str,
    focus_areas: list[Category],
    recency_window: str,
    ledger: EvidenceLedger,
    settings: Settings | None = None,
    model=None,
) -> SynthesisResult:
    """Produce a grounded ``DraftBrief`` from the evidence ledger."""
    settings = settings or get_settings()
    if ledger.is_empty():
        return SynthesisResult(draft=DraftBrief(executive_summary="", findings=[]))

    model = model or build_model(settings)
    method = "json_schema" if settings.resolve_provider() == "openai" else "function_calling"
    structured = model.with_structured_output(
        DraftBrief, method=method, include_raw=True
    )

    human = (
        f"Company: {company}\n"
        f"Focus areas: {', '.join(focus_areas)}\n"
        f"Recency window: last {recency_window}\n\n"
        f"Evidence (cite by id):\n\n{ledger.render_context()}"
    )
    result = structured.invoke(
        [
            {"role": "system", "content": SYNTHESIS_SYSTEM},
            {"role": "user", "content": human},
        ]
    )

    if isinstance(result, dict):
        draft = result.get("parsed") or DraftBrief(executive_summary="", findings=[])
        prompt_tokens, completion_tokens = _usage(result.get("raw"))
    else:
        draft = result
        prompt_tokens = completion_tokens = None

    return SynthesisResult(
        draft=draft, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens
    )
