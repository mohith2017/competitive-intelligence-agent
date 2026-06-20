"""
Query enhancement: turn a bare company name into focused, 
category-specific search queries.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Category

CATEGORY_QUERY_TEMPLATES: dict[Category, list[str]] = {
    "funding": [
        "{company} funding round amount valuation investors",
    ],
    "financials": [
        "{company} revenue ARR growth financial results",
    ],
    "product": [
        "{company} product launch new feature announcement",
    ],
    "pricing": [
        "{company} pricing plans cost per seat enterprise tier",
    ],
    "hiring": [
        "{company} hiring headcount layoffs key executive appointment",
    ],
    "partnerships": [
        "{company} partnership integration customer deal",
    ],
    "market_positioning": [
        "{company} market position competitors differentiation strategy",
    ],
    "risk": [
        "{company} lawsuit regulatory risk security incident controversy",
    ],
}


@dataclass(frozen=True)
class PlanItem:
    """A single (category, query) unit of retrieval work."""

    category: Category
    query: str


def build_plan(company: str, focus_areas: list[Category]) -> list[PlanItem]:
    """Expand the company + focus areas into category-specific sub-queries."""
    company = company.strip()
    plan: list[PlanItem] = []
    for category in focus_areas:
        for template in CATEGORY_QUERY_TEMPLATES.get(category, []):
            plan.append(PlanItem(category=category, query=template.format(company=company)))
    return plan


def refine_query(item: PlanItem, company: str) -> PlanItem:
    """Broaden a query for the single self-correction retry."""
    return PlanItem(
        category=item.category,
        query=f"{company.strip()} {item.category.replace('_', ' ')} latest news 2026",
    )
