"""Deterministic tests for the Hybrid RAG agent (Tavily Evidence Fusion)."""

from __future__ import annotations

from competitive_intel import run_brief
from competitive_intel.config import get_settings
from competitive_intel.models import DraftBrief, Finding, SearchResult
from competitive_intel.pipeline.ledger import build_ledger
from competitive_intel.pipeline.plan import build_plan
from competitive_intel.pipeline.rerank import fuse_category
from competitive_intel.pipeline.verify import normalize_citation_id, verify
from competitive_intel.tools.tavily_tools import extracted_from_payload, results_from_payload


def _settings():
    return get_settings()


def test_build_plan_covers_each_focus_area():
    plan = build_plan("Acme", ["funding", "product"])
    categories = {item.category for item in plan}
    assert {"funding", "product"} <= categories
    assert all("Acme" in item.query for item in plan)


def test_fusion_ranks_and_scores_relevant_passage_higher():
    query = "Acme Series B funding round investors amount"
    results = [
        SearchResult(
            url="https://rel.com",
            title="Acme raises Series B",
            content="Acme closed a Series B funding round with new investors and capital.",
            score=0.9,
            category="funding",
        ),
        SearchResult(
            url="https://noise1.com",
            title="Weather report",
            content="Skies are clear today with mild temperatures and light wind.",
            score=0.7,
            category="funding",
        ),
        SearchResult(
            url="https://noise2.com",
            title="Recipe blog",
            content="Combine flour and sugar, then bake the cake for thirty minutes.",
            score=0.5,
            category="funding",
        ),
    ]
    passages = fuse_category(query, results, _settings())
    by_url = {p.url: p for p in passages}
    assert by_url["https://rel.com"].bm25_score > by_url["https://noise1.com"].bm25_score
    assert by_url["https://rel.com"].bm25_score > by_url["https://noise2.com"].bm25_score
    assert passages[0].url == "https://rel.com"
    assert passages == sorted(passages, key=lambda p: p.fused_score, reverse=True)


def test_ledger_dedupes_and_assigns_stable_ids():
    shared = SearchResult(
        url="https://dup.com",
        title="Shared source",
        content="Acme funding and product details in one article.",
        score=0.9,
        category="funding",
    )
    funding = fuse_category("Acme funding", [shared], _settings())
    product = fuse_category("Acme product", [shared], _settings())
    ledger = build_ledger({"funding": funding, "product": product})
    assert len(ledger.citations) == 1
    assert ledger.citations[0].id == "S1"


def test_normalize_citation_id_variants():
    assert normalize_citation_id("S1") == "S1"
    assert normalize_citation_id("[S1]") == "S1"
    assert normalize_citation_id("s01") == "S1"
    assert normalize_citation_id("3") == "S3"
    assert normalize_citation_id("nope") is None


def test_verify_drops_unsupported_and_computes_coverage():
    result = SearchResult(
        url="https://a.com",
        title="Acme raises $60M",
        content="Acme raised $60M Series B.",
        score=0.9,
        published_date="2026-06-10",
        category="funding",
    )
    ledger = build_ledger({"funding": fuse_category("Acme funding", [result], _settings())})
    draft = DraftBrief(
        executive_summary="Acme raised money.",
        findings=[
            Finding(category="funding", claim="Raised $60M", confidence="high",
                    citation_ids=["[S1]"]),
            Finding(category="funding", claim="Hallucinated", confidence="low",
                    citation_ids=["S9"]),
        ],
    )
    brief = verify(draft, ledger, company="Acme", recency_window="month",
                   focus_areas=["funding"], generated_at="2026-06-19")
    assert len(brief.findings) == 1
    assert len(brief.dropped_findings) == 1
    assert brief.citation_coverage == 0.5
    assert [s.id for s in brief.sources] == ["S1"]
    assert brief.findings[0].citation_ids == ["S1"]


def test_payload_normalizers_handle_search_and_extract():
    payload = {
        "results": [
            {"url": "https://a.com", "title": "T", "content": "snippet",
             "raw_content": "full", "score": 0.8, "published_date": "2026-06-10"},
            {"title": "no url"},
        ]
    }
    results = results_from_payload(payload, "funding")
    assert len(results) == 1
    assert results[0].url == "https://a.com"
    assert results[0].best_text() == "full"
    assert results[0].category == "funding"

    extracted = extracted_from_payload(
        {"results": [{"url": "https://a.com", "raw_content": "page text"}]}
    )
    assert extracted == {"https://a.com": "page text"}


def test_run_brief_end_to_end_is_grounded(patched_pipeline):
    brief, summary = run_brief(
        "Acme",
        focus_areas=["funding"],
        recency_window="month",
        configure_observability=False,
    )
    assert brief.company == "Acme"
    assert summary.n_findings == 1
    assert brief.citation_coverage == 1.0
    listed = {s.id for s in brief.sources}
    for finding in brief.findings:
        assert finding.citation_ids
        assert set(finding.citation_ids) <= listed
    assert summary.retries == 0
