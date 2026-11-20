
from bs4 import BeautifulSoup
from opportunity_intelligence.collectors.web_collector import fetch_page


def test_fetch_page_returns_html():
    """Test that a webpage can be retrieved and parsed."""

    result = fetch_page("https://example.com")

    assert isinstance(result, BeautifulSoup)
    assert result.title is not None
    assert "Example" in result.title.text
