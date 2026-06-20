from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal[
    "funding",
    "financials",
    "product",
    "pricing",
    "hiring",
    "partnerships",
    "market_positioning",
    "risk",
]

CATEGORIES: tuple[Category, ...] = (
    "funding",
    "financials",
    "product",
    "pricing",
    "hiring",
    "partnerships",
    "market_positioning",
    "risk",
)

Confidence = Literal["high", "med", "low"]


class SearchResult(BaseModel):
    """A single raw result returned by Tavily search/extract."""

    url: str
    title: str = "Untitled"
    content: str = Field(default="", description="Tavily snippet for the result.")
    raw_content: str | None = Field(
        default=None, description="Full extracted page text, when available."
    )
    score: float = Field(default=0.0, description="Tavily relevance score (0-1).")
    published_date: str | None = None
    category: Category | None = Field(
        default=None, description="Category whose query surfaced this result."
    )

    def best_text(self) -> str:
        """Prefer extracted full text, fall back to the snippet."""
        return (self.raw_content or self.content or "").strip()


class Passage(BaseModel):
    """A scored, fusion-ranked chunk of evidence tied to one source URL."""
    url: str
    title: str = "Untitled"
    text: str
    published_date: str | None = None
    category: Category | None = None
    tavily_score: float = 0.0
    bm25_score: float = 0.0
    fused_score: float = Field(
        default=0.0, description="Reciprocal-rank-fusion of Tavily + BM25 ranks."
    )


class Citation(BaseModel):
    id: str = Field(description="Stable citation id, e.g. 'S1'.")
    title: str
    url: str
    published_date: str | None = None


class EvidenceLedger(BaseModel):
    """The compact, deduped, citable context handed to the synthesis model."""
    passages: list[Passage] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)

    def citation_map(self) -> dict[str, Citation]:
        return {c.id: c for c in self.citations}

    def url_to_id(self) -> dict[str, str]:
        return {c.url: c.id for c in self.citations}

    def is_empty(self) -> bool:
        return not self.passages

    def render_context(self) -> str:
        """Render the ledger as the grounding block for the synthesis prompt."""
        id_for_url = self.url_to_id()
        lines: list[str] = []
        for passage in self.passages:
            sid = id_for_url.get(passage.url, "?")
            date = passage.published_date or "date unknown"
            cat = passage.category or "general"
            lines.append(
                f"[{sid}] ({cat}; as of {date}) {passage.title}\n{passage.text}"
            )
        return "\n\n".join(lines)


class Finding(BaseModel):
    """One grounded claim about the target company."""
    category: Category = Field(description="Which diligence bucket this belongs to.")
    claim: str = Field(description="A single, specific, factual statement.")
    confidence: Confidence = Field(
        description="high = multiple/primary sources; med = one solid source; low = weak/indirect."
    )
    as_of: str | None = Field(
        default=None, description="Date the fact was true, ideally YYYY-MM-DD."
    )
    citation_ids: list[str] = Field(
        default_factory=list,
        description="Source ids from the evidence ledger, e.g. ['S1', 'S3'].",
    )


class DraftBrief(BaseModel):
    """The synthesis model's structured output (before verification)."""

    executive_summary: str = Field(
        description="3-5 sentences a finance analyst could paste into a memo."
    )
    findings: list[Finding] = Field(default_factory=list)


class Brief(BaseModel):
    """The final, verified competitive intelligence brief."""
    company: str
    generated_at: str
    recency_window: str
    focus_areas: list[Category] = Field(default_factory=list)
    executive_summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    citation_coverage: float = Field(
        default=0.0,
        description="Fraction of findings supported by >=1 resolvable citation.",
    )
    dropped_findings: list[Finding] = Field(
        default_factory=list,
        description="Findings removed by verification (unsupported citations).",
    )

class RetrievalSpanMeta(BaseModel):
    """Compact, loggable summary of a retrieval/rerank stage for a category."""
    stage: str
    category: Category | None = None
    query: str = ""
    n_results: int = 0
    n_passages: int = 0
    top_k_ids: list[str] = Field(default_factory=list)
    max_fused_score: float = 0.0
    mean_fused_score: float = 0.0
    retried: bool = False


class RunSummary(BaseModel):
    """End-to-end run summary, logged once per brief."""
    company: str
    recency_window: str
    focus_areas: list[Category] = Field(default_factory=list)
    provider: str = ""
    model: str = ""
    n_sources: int = 0
    n_findings: int = 0
    n_dropped: int = 0
    citation_coverage: float = 0.0
    retries: int = 0
    duration_s: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
