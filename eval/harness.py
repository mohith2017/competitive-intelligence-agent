"""Standalone runner for the deterministic evaluation suite."""

from __future__ import annotations

import sys

from rich.console import Console

from competitive_intel.evals import format_report, run_eval


def main() -> int:
    cases = sys.argv[1] if len(sys.argv) > 1 else "eval/cases.yaml"
    report = run_eval(cases)
    Console().print(format_report(report))
    return 0 if report.pass_rate > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
