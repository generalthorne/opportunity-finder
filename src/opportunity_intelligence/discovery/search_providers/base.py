
"""Shared interface and result model for web search providers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class SearchResult:
    """A normalized result returned by a search provider."""

    query: str
    title: str
    url: str
    snippet: str
    score: float | None = None
    published_date: str | None = None


class SearchProvider(Protocol):
    """Interface implemented by web search providers."""

    def search(
        self,
        query: str,
        max_results: int = 10
    ) -> list[SearchResult]:
        """Search the web and return normalized results."""
        ...
