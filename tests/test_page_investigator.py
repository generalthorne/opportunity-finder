
import json

from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import FetchResult
from opportunity_intelligence.discovery.page_investigator import (
    investigate_page,
    investigate_pages,
    save_investigation_results
)


def test_investigate_page_success(monkeypatch):
    """Test that a successfully retrieved page is extracted."""

    def mock_fetch_page(url):
        return FetchResult(
            soup=BeautifulSoup(
                """
                <html>
                    <head><title>Summer Research Program</title></head>
                    <body>
                        <h1>Research Opportunity</h1>
                        <p>Applications are now open.</p>
                    </body>
                </html>
                """,
                "html.parser"
            ),
            status_code=200,
            error=None
        )

    monkeypatch.setattr(
        "opportunity_intelligence.discovery.page_investigator.fetch_page",
        mock_fetch_page
    )

    link = {
        "url": "https://example.com/research",
        "text": "Summer Research Fellowship",
        "link_type": "opportunity",
        "relevance_score": 8,
        "matched_keywords": ["summer", "research"],
        "discovered_in": []
    }

    result = investigate_page(link)

    assert result["status"] == "success"
    assert result["http_status_code"] == 200
    assert result["error"] is None
    assert result["page_title"] == "Summer Research Program"
    assert "Applications are now open." in result["page_text"]
    assert result["relevance_score"] == 8
    assert result["cache_status"] == "downloaded"


def test_investigate_page_failure(monkeypatch):
    """Test that a failed retrieval is recorded correctly."""

    def mock_fetch_page(url):
        return FetchResult(
            soup=None,
            status_code=403,
            error="403 Client Error: Forbidden"
        )

    monkeypatch.setattr(
        "opportunity_intelligence.discovery.page_investigator.fetch_page",
        mock_fetch_page
    )

    link = {
        "url": "https://example.com/research",
        "text": "Summer Research Fellowship",
        "link_type": "opportunity",
        "relevance_score": 8
    }

    result = investigate_page(link)

    assert result["status"] == "failed"
    assert result["http_status_code"] == 403
    assert result["error"] == "403 Client Error: Forbidden"
    assert result["page_title"] is None
    assert result["page_text"] is None
    assert result["cache_status"] == "not_cached"


def test_investigate_pages(tmp_path, monkeypatch):
    """Test that multiple prioritized links are investigated."""

    input_file = tmp_path / "prioritized_links.json"

    data = {
        "links": [
            {"url": "https://example.com/one"},
            {"url": "https://example.com/two"}
        ]
    }

    input_file.write_text(
        json.dumps(data),
        encoding="utf-8"
    )

    def mock_investigate_page(link, cache=None):
        return {
            "url": link["url"],
            "status": "success",
            "page_title": "Test Page",
            "page_text": "Test content",
            "cache_status": "downloaded"
        }

    monkeypatch.setattr(
        "opportunity_intelligence.discovery.page_investigator.investigate_page",
        mock_investigate_page
    )

    results = investigate_pages(
        input_file=input_file,
        delay_seconds=0
    )

    assert len(results) == 2
    assert results[0]["status"] == "success"
    assert results[1]["status"] == "success"
    assert results[0]["cache_status"] == "downloaded"
    assert results[1]["cache_status"] == "downloaded"


def test_save_investigation_results(tmp_path):
    """Test that investigation results are saved correctly."""

    output_file = tmp_path / "investigated_pages.json"

    results = [
        {
            "url": "https://example.com/one",
            "status": "success",
            "page_title": "Test Page",
            "page_text": "Test content",
            "cache_status": "downloaded"
        },
        {
            "url": "https://example.com/two",
            "status": "failed",
            "page_title": None,
            "page_text": None,
            "cache_status": "not_cached"
        }
    ]

    save_investigation_results(
        results,
        output_file
    )

    assert output_file.exists()

    saved_data = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert saved_data["total_pages"] == 2
    assert saved_data["successful_pages"] == 1
    assert saved_data["failed_pages"] == 1
