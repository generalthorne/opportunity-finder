
"""Tavily implementation of the shared search provider interface."""

import os

import requests
from dotenv import load_dotenv

from opportunity_intelligence.discovery.search_providers.base import (
    SearchResult
)


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearchProvider:
    """Search the web using the Tavily Search API."""

    def __init__(self, api_key: str | None = None) -> None:
        load_dotenv()

        self.api_key = api_key or os.getenv("TAVILY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY was not found. "
                "Add it to the project-root .env file."
            )

    def search(
        self,
        query: str,
        max_results: int = 10
    ) -> list[SearchResult]:
        """Run a basic Tavily search and normalize its results."""

        if not query.strip():
            raise ValueError("Search query cannot be empty.")

        if not 1 <= max_results <= 20:
            raise ValueError("max_results must be between 1 and 20.")

        response = requests.post(
            TAVILY_SEARCH_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
                "include_images": False
            },
            timeout=30
        )

        response.raise_for_status()
        data = response.json()

        results = []

        for item in data.get("results", []):
            url = item.get("url")
            title = item.get("title")

            if not url or not title:
                continue

            results.append(
                SearchResult(
                    query=query,
                    title=title,
                    url=url,
                    snippet=item.get("content", ""),
                    score=item.get("score"),
                    published_date=item.get("published_date")
                )
            )

        return results
