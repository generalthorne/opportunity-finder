import requests

from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import fetch_page


def test_fetch_page_returns_html(monkeypatch):
    """Test that a successful request returns parsed HTML."""

    class MockResponse:
        status_code = 200
        text = """
        <html>
            <head><title>Example Domain</title></head>
            <body><h1>Example</h1></body>
        </html>
        """
        headers = {}
        def raise_for_status(self):
            pass

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse()
    )

    result = fetch_page("https://example.com")

    assert isinstance(result.soup, BeautifulSoup)
    assert result.status_code == 200
    assert result.error is None
    assert result.soup.title is not None
    assert "Example" in result.soup.title.get_text()


def test_fetch_page_handles_http_error(monkeypatch):
    """Test that an HTTP error is recorded correctly."""

    class MockResponse:
        status_code = 403
        headers = {}

        def raise_for_status(self):
            raise requests.HTTPError(
                "403 Client Error: Forbidden",
                response=self
            )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: MockResponse()
    )

    result = fetch_page("https://example.com")

    assert result.soup is None
    assert result.status_code == 403
    assert result.error is not None
    assert "403" in result.error