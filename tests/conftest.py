"""Shared test fixtures. All tests are deterministic and never hit the network."""

from __future__ import annotations

import pytest

from competitive_intel.config import get_settings
from competitive_intel.models import DraftBrief, Finding, SearchResult
from competitive_intel.pipeline import orchestrator
from competitive_intel.pipeline.synthesize import SynthesisResult


@pytest.fixture
def patched_pipeline(monkeypatch):
    """
    Patch the orchestrator's Tavily + synthesis so run_brief is hermetic.
    """

    class FakeRetriever:
        def __init__(self, settings=None):
            self.settings = settings

        def search(self, query, *, category=None, **kwargs):
            return [
                SearchResult(
                    url=f"https://example.com/{category}",
                    title=f"{category} headline",
                    content=f"{query}. Detailed {category} update for the company.",
                    score=0.8,
                    published_date="2026-06-12",
                    category=category,
                )
            ]

        def extract(self, urls, **kwargs):
            return {}

    def fake_synth(company, focus_areas, recency_window, ledger, settings=None, model=None):
        cid = ledger.citations[0].id if ledger.citations else "S1"
        draft = DraftBrief(
            executive_summary=f"{company} summary.",
            findings=[
                Finding(
                    category=focus_areas[0],
                    claim="A grounded claim about the company.",
                    confidence="high",
                    as_of="2026-06-12",
                    citation_ids=[cid],
                )
            ],
        )
        return SynthesisResult(draft=draft, prompt_tokens=42, completion_tokens=17)

    keyed = get_settings().model_copy(
        update={"anthropic_api_key": "test-key", "provider": "anthropic"}
    )

    monkeypatch.setattr(orchestrator, "TavilyRetriever", FakeRetriever)
    monkeypatch.setattr(orchestrator, "synthesize", fake_synth)
    monkeypatch.setattr(orchestrator, "get_settings", lambda: keyed)
    return orchestrator
