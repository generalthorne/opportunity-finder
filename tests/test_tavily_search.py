
from unittest.mock import Mock, patch

import pytest

from opportunity_intelligence.discovery.search_providers.tavily import (
    TavilySearchProvider
)


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)

    with patch(
        "opportunity_intelligence.discovery.search_providers.tavily.load_dotenv"
    ):
        with pytest.raises(ValueError, match="TAVILY_API_KEY"):
            TavilySearchProvider()


@patch(
    "opportunity_intelligence.discovery.search_providers.tavily.requests.post"
)
def test_search_returns_normalized_results(mock_post):
    mock_response = Mock()
    mock_response.json.return_value = {
        "results": [
            {
                "title": "Undergraduate Research Program",
                "url": "https://example.edu/research",
                "content": "Research opportunities for undergraduate students.",
                "score": 0.95,
                "published_date": None
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    provider = TavilySearchProvider(api_key="test-key")
    results = provider.search("undergraduate research", max_results=5)

    assert len(results) == 1
    assert results[0].title == "Undergraduate Research Program"
    assert results[0].url == "https://example.edu/research"
    assert results[0].query == "undergraduate research"
    assert results[0].score == 0.95

    mock_post.assert_called_once()


def test_search_rejects_empty_query():
    provider = TavilySearchProvider(api_key="test-key")

    with pytest.raises(ValueError, match="cannot be empty"):
        provider.search("   ")


def test_search_rejects_invalid_result_limit():
    provider = TavilySearchProvider(api_key="test-key")

    with pytest.raises(ValueError, match="between 1 and 20"):
        provider.search("undergraduate research", max_results=25)
