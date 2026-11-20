
import json

from bs4 import BeautifulSoup

from opportunity_intelligence.discovery.source_registry import Source
import opportunity_intelligence.discovery.collect_sources as collector


def create_test_source() -> Source:
    return Source(
        id="test_source",
        name="Test University",
        url="https://example.com",
        region="Canada",
        source_type="university",
        categories=["research"],
        enabled=True
    )


def test_extract_links():
    html = """
    <html>
        <body>
            <a href="/research">Research Opportunities</a>
            <a href="https://example.com/jobs">Student Jobs</a>
            <a href="mailto:test@example.com">Email</a>
            <a href="/research">Duplicate Link</a>
        </body>
    </html>
    """

    soup = BeautifulSoup(html, "html.parser")

    links = collector.extract_links(soup, "https://example.com")

    assert len(links) == 2
    assert links[0]["text"] == "Research Opportunities"
    assert links[0]["url"] == "https://example.com/research"
    assert links[1]["url"] == "https://example.com/jobs"


def test_collect_source_success(monkeypatch):
    html = """
    <html>
        <head><title>Test University</title></head>
        <body>
            <h1>Research Opportunities</h1>
            <p>Summer research positions available.</p>
            <a href="/research">Research Programs</a>
        </body>
    </html>
    """

    monkeypatch.setattr(
        collector,
        "fetch_page",
        lambda url: BeautifulSoup(html, "html.parser")
    )

    result = collector.collect_source(create_test_source())

    assert result["status"] == "success"
    assert result["page_title"] == "Test University"
    assert "Summer research positions available." in result["page_text"]
    assert len(result["links"]) == 1
    assert result["links"][0]["url"] == "https://example.com/research"


def test_collect_source_failure(monkeypatch):
    monkeypatch.setattr(collector, "fetch_page", lambda url: None)

    result = collector.collect_source(create_test_source())

    assert result["status"] == "failed"
    assert result["page_text"] is None
    assert result["links"] == []


def test_save_record(tmp_path):
    record = {
        "source_id": "test_source",
        "status": "success",
        "page_title": "Test University"
    }

    collector.save_record(record, tmp_path)

    output_file = tmp_path / "test_source.json"

    assert output_file.exists()

    with output_file.open("r", encoding="utf-8") as file:
        saved_record = json.load(file)

    assert saved_record["page_title"] == "Test University"


def test_collect_sources(monkeypatch, tmp_path):
    source = create_test_source()

    monkeypatch.setattr(
        collector,
        "collect_source",
        lambda source: {
            "source_id": source.id,
            "status": "success",
            "links": []
        }
    )

    results = collector.collect_sources(
        sources=[source],
        output_dir=tmp_path,
        delay_seconds=0
    )

    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert (tmp_path / "test_source.json").exists()
