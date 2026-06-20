"""Deterministic tests for the eval metrics and observability artifacts."""

from __future__ import annotations

from datetime import date

from competitive_intel import observability, run_brief
from competitive_intel.evals import (
    compute_metrics,
    is_pass,
    source_validity,
)
from competitive_intel.models import Brief, Citation, Finding, RetrievalSpanMeta, RunSummary


def _brief(findings, sources, *, window="month", coverage=1.0):
    return Brief(
        company="Acme",
        generated_at="2026-06-19",
        recency_window=window,
        focus_areas=["funding"],
        executive_summary="summary",
        findings=findings,
        sources=sources,
        citation_coverage=coverage,
    )


def _source(sid, published_date):
    return Citation(id=sid, url=f"https://ex.com/{sid}", title=sid,
                    published_date=published_date)


def test_source_validity_detects_dangling_citation():
    sources = [_source("S1", "2026-06-10")]
    good = _brief([Finding(category="funding", claim="c", confidence="high",
                           citation_ids=["S1"])], sources)
    bad = _brief([Finding(category="funding", claim="c", confidence="high",
                          citation_ids=["S1", "S2"])], sources, coverage=1.0)
    assert source_validity(good) == 1.0
    assert source_validity(bad) == 0.5


def test_recency_adherence_respects_window():
    sources = [_source("S1", "2026-06-10"), _source("S2", "2026-01-01")]
    finding = Finding(category="funding", claim="c", confidence="high",
                      citation_ids=["S1", "S2"])
    metrics = compute_metrics(_brief([finding], sources, window="month"),
                              today=date(2026, 6, 19))
    assert metrics["recency_adherence"] == 0.5


def test_compute_metrics_bundle_and_pass():
    sources = [_source("S1", "2026-06-10")]
    finding = Finding(category="funding", claim="c", confidence="high",
                      citation_ids=["S1"])
    metrics = compute_metrics(_brief([finding], sources), today=date(2026, 6, 19))
    assert metrics["citation_coverage"] == 1.0
    assert metrics["source_validity"] == 1.0
    assert metrics["recency_adherence"] == 1.0
    assert is_pass(metrics) is True


def test_empty_brief_does_not_pass():
    metrics = compute_metrics(_brief([], [], coverage=0.0), today=date(2026, 6, 19))
    assert is_pass(metrics) is False


def test_observability_artifacts_emitted_during_run(patched_pipeline, monkeypatch):
    """The pipeline must log typed RetrievalSpanMeta + RunSummary artifacts."""
    captured: list[tuple[str, object]] = []

    def fake_log_model(name, model):
        captured.append((name, model))

    monkeypatch.setattr(patched_pipeline, "log_model", fake_log_model)

    run_brief("Acme", focus_areas=["funding"], recency_window="month",
              configure_observability=False)

    kinds = {name: model for name, model in captured}
    assert any(isinstance(m, RetrievalSpanMeta) for m in kinds.values())
    assert any(isinstance(m, RunSummary) for m in kinds.values())
    for _name, model in captured:
        assert isinstance(model.model_dump(), dict)


def test_span_and_log_model_are_safe_noops_without_logfire():
    """Observability degrades gracefully when Logfire isn't configured."""
    with observability.span("unit_test", foo="bar"):
        pass
    observability.log_model(
        "retrieval",
        RetrievalSpanMeta(stage="retrieve_rerank", n_results=0, n_passages=0),
    )
