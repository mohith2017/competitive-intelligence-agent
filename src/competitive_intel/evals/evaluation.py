"""Deterministic evaluation of briefs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from rich.table import Table

from .. import run_brief
from ..models import Brief
from ..pipeline.render import render_markdown
from ..pipeline.verify import recency_adherence


def source_validity(brief: Brief) -> float:
    """Fraction of all cited ids (across kept findings) that resolve to a source."""
    valid = {s.id for s in brief.sources}
    cited = [cid for f in brief.findings for cid in f.citation_ids]
    if not cited:
        return 1.0 if not brief.findings else 0.0
    return round(sum(1 for c in cited if c in valid) / len(cited), 3)


def compute_metrics(brief: Brief, *, today: date | None = None) -> dict[str, float]:
    """Deterministic metric bundle for a single brief."""
    return {
        "citation_coverage": brief.citation_coverage,
        "source_validity": source_validity(brief),
        "recency_adherence": recency_adherence(
            brief.sources, brief.recency_window, today=today
        ),
        "n_findings": float(len(brief.findings)),
        "n_sources": float(len(brief.sources)),
        "n_dropped": float(len(brief.dropped_findings)),
    }


def is_pass(metrics: dict[str, float]) -> bool:
    """A case passes if it produced grounded, fully-resolvable findings."""
    return (
        metrics["n_findings"] > 0
        and metrics["citation_coverage"] > 0
        and metrics["source_validity"] >= 1.0
    )


@dataclass
class CaseResult:
    company: str
    metrics: dict[str, float]
    passed: bool


@dataclass
class EvalReport:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def aggregate(self) -> dict[str, float]:
        if not self.results:
            return {}
        keys = self.results[0].metrics.keys()
        return {
            k: round(sum(r.metrics[k] for r in self.results) / len(self.results), 3)
            for k in keys
        }

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return round(sum(1 for r in self.results if r.passed) / len(self.results), 3)


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data.get("cases", [])


def run_eval(cases_path: str | Path, out_prefix: str | None = None) -> EvalReport:
    """Run live briefs for each case and score them deterministically."""
    report = EvalReport()
    for case in load_cases(cases_path):
        company = case["company"]
        focus = case.get("focus")
        window = case.get("window")
        brief, _summary = run_brief(
            company, focus_areas=focus, recency_window=window
        )
        if out_prefix:
            slug = company.lower().replace(" ", "_")
            Path(f"{out_prefix}{slug}.md").write_text(
                render_markdown(brief), encoding="utf-8"
            )
        metrics = compute_metrics(brief)
        report.results.append(
            CaseResult(company=company, metrics=metrics, passed=is_pass(metrics))
        )
    return report


def format_report(report: EvalReport):
    """Render an ``EvalReport`` as a rich table."""
    table = Table(title="Deterministic evaluation", title_style="bold cyan")
    table.add_column("Company")
    table.add_column("Coverage", justify="right")
    table.add_column("Src valid", justify="right")
    table.add_column("Recency", justify="right")
    table.add_column("Findings", justify="right")
    table.add_column("Pass", justify="center")

    for r in report.results:
        m = r.metrics
        table.add_row(
            r.company,
            f"{round(m['citation_coverage'] * 100)}%",
            f"{round(m['source_validity'] * 100)}%",
            f"{round(m['recency_adherence'] * 100)}%",
            str(int(m["n_findings"])),
            "[green]PASS[/]" if r.passed else "[red]FAIL[/]",
        )

    agg = report.aggregate
    if agg:
        table.add_section()
        table.add_row(
            "[bold]Average[/]",
            f"{round(agg['citation_coverage'] * 100)}%",
            f"{round(agg['source_validity'] * 100)}%",
            f"{round(agg['recency_adherence'] * 100)}%",
            f"{agg['n_findings']:.1f}",
            f"{round(report.pass_rate * 100)}%",
        )
    return table
