from __future__ import annotations

import argparse
from pathlib import Path

from competitive_intel import run_brief
from competitive_intel.pipeline.render import render_markdown

OUT = Path(__file__).with_name("sample_brief.md")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a sample brief.")
    parser.add_argument("company", nargs="?", default="Perplexity")
    parser.add_argument("--focus", default="funding,product,pricing")
    parser.add_argument("--window", default="month")
    args = parser.parse_args()

    focus = [c.strip() for c in args.focus.split(",") if c.strip()]
    brief, summary = run_brief(args.company, focus_areas=focus, recency_window=args.window)
    OUT.write_text(render_markdown(brief), encoding="utf-8")
    print(f"Wrote {OUT} — coverage {round(summary.citation_coverage * 100)}%, "
          f"{summary.n_sources} sources, {summary.n_findings} findings.")


if __name__ == "__main__":
    main()
