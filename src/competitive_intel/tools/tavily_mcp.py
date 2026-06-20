from __future__ import annotations

import asyncio
from typing import Any

from ..config import Settings, get_settings
from ..models import Category, SearchResult
from .tavily_tools import _as_dict, extracted_from_payload, results_from_payload

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
except ImportError:
    MultiServerMCPClient = None

TAVILY_MCP_URL = "https://mcp.tavily.com/mcp/"


class McpTavilyRetriever:
    """Tavily retrieval through the hosted Tavily MCP server."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is required for --via-mcp.")
        if MultiServerMCPClient is None:
            raise RuntimeError(
                "--via-mcp needs the optional dependency. Install with: "
                "pip install 'competitive-intel-agent[mcp]'"
            )

        url = f"{TAVILY_MCP_URL}?tavilyApiKey={self.settings.tavily_api_key}"
        self._client = MultiServerMCPClient(
            {"tavily": {"transport": "streamable_http", "url": url}}
        )

    async def _acall(self, tool_name: str, args: dict[str, Any]) -> Any:
        tools = {t.name: t for t in await self._client.get_tools()}
        tool = tools.get(tool_name) or next(
            (t for name, t in tools.items() if name.endswith(tool_name)), None
        )
        if tool is None:
            raise RuntimeError(
                f"Tavily MCP tool '{tool_name}' not found. Available: {list(tools)}"
            )
        return await tool.ainvoke(args)

    def _call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return _as_dict(asyncio.run(self._acall(tool_name, args)))

    def search(
        self,
        query: str,
        *,
        category: Category | None = None,
        topic: str = "finance",
        time_range: str | None = None,
        search_depth: str = "advanced",
        max_results: int | None = None,
        include_domains: list[str] | None = None,
    ) -> list[SearchResult]:
        payload = self._call(
            "tavily_search",
            {
                "query": query,
                "topic": topic,
                "search_depth": search_depth,
                "time_range": time_range or self.settings.default_recency_window,
                "max_results": max_results or self.settings.results_per_query,
                "include_raw_content": True,
            },
        )
        return results_from_payload(payload, category)

    def extract(self, urls: list[str], *, extract_depth: str = "advanced") -> dict[str, str]:
        urls = [u for u in dict.fromkeys(urls) if u]
        if not urls:
            return {}
        payload = self._call(
            "tavily_extract", {"urls": urls, "extract_depth": extract_depth}
        )
        return extracted_from_payload(payload)
