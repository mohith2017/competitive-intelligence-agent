from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import run_brief
from .config import get_settings
from .evals import format_report, run_eval
from .models import CATEGORIES, Category
from .pipeline.render import render_markdown
from .tools.tavily_mcp import McpTavilyRetriever

console = Console()


def _parse_focus(focus: str | None, default: list[Category]) -> list[Category]:
    if not focus:
        return default
    requested = [part.strip().lower() for part in focus.split(",") if part.strip()]
    invalid = [r for r in requested if r not in CATEGORIES]
    if invalid:
        raise click.BadParameter(
            f"unknown categories: {', '.join(invalid)}. "
            f"Valid: {', '.join(CATEGORIES)}"
        )
    return [r for r in requested if r in CATEGORIES]


@click.group()
@click.version_option(package_name="competitive-intel-agent")
def cli() -> None:
    """Source-verified competitive intelligence briefs powered by Tavily."""


@cli.command()
@click.argument("company")
@click.option("--focus", default=None, help="Comma-separated categories (default: all).")
@click.option(
    "--window",
    "recency_window",
    default=None,
    type=click.Choice(["day", "week", "month", "year"]),
    help="Recency window for retrieval (Tavily time_range).",
)
@click.option(
    "--provider",
    default=None,
    type=click.Choice(["anthropic", "openai"]),
    help="Override the synthesis model provider.",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Write the markdown brief to this path instead of stdout.",
)
@click.option(
    "--via-mcp",
    is_flag=True,
    default=False,
    help="Stretch: retrieve through the Tavily MCP server (needs the 'mcp' extra).",
)
def brief(
    company: str,
    focus: str | None,
    recency_window: str | None,
    provider: str | None,
    out: str | None,
    via_mcp: bool,
) -> None:
    """Generate a competitive intelligence brief for COMPANY."""
    settings = get_settings()
    if provider:
        settings = settings.model_copy(update={"provider": provider})
    focus_areas = _parse_focus(focus, settings.default_categories)
    window = recency_window or settings.default_recency_window

    if not settings.tavily_api_key:
        raise click.ClickException("Missing TAVILY_API_KEY (see .env.template).")

    retriever = None
    if via_mcp:
        try:
            retriever = McpTavilyRetriever(settings)
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc

    label = " via Tavily MCP" if via_mcp else ""
    with console.status(
        f"[bold cyan]Researching {company}[/]{label} (last {window})...", spinner="dots"
    ):
        try:
            result, summary = run_brief(
                company,
                focus_areas=focus_areas,
                recency_window=window,
                settings=settings,
                retriever=retriever,
            )
        except Exception as exc:
            raise click.ClickException(str(exc)) from exc

    markdown = render_markdown(result)
    if out:
        Path(out).write_text(markdown, encoding="utf-8")
        console.print(f"[green]Wrote brief to[/] {out}")
    else:
        console.print(markdown)

    _print_summary(summary)


def _print_summary(summary) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_row("Provider / model", f"{summary.provider} / {summary.model}")
    table.add_row("Sources cited", str(summary.n_sources))
    table.add_row("Findings (kept / dropped)", f"{summary.n_findings} / {summary.n_dropped}")
    table.add_row("Citation coverage", f"{round(summary.citation_coverage * 100)}%")
    table.add_row("Self-correction retries", str(summary.retries))
    table.add_row("Duration", f"{summary.duration_s}s")
    if summary.prompt_tokens is not None:
        table.add_row(
            "Tokens (in / out)",
            f"{summary.prompt_tokens} / {summary.completion_tokens}",
        )
    console.print(Panel(table, title="Run summary", border_style="cyan"))


@cli.command(name="eval")
@click.option(
    "--cases",
    type=click.Path(exists=True, dir_okay=False),
    default="eval/cases.yaml",
    show_default=True,
    help="YAML file of evaluation cases.",
)
@click.option(
    "--out",
    type=click.Path(dir_okay=False, writable=True),
    default=None,
    help="Optionally write per-case briefs under this directory prefix.",
)
def eval_cmd(cases: str, out: str | None) -> None:
    """Run the deterministic evaluation suite over a set of cases."""
    report = run_eval(cases, out_prefix=out)
    console.print(format_report(report))


if __name__ == "__main__":
    cli()
