
from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import FetchResult
from opportunity_intelligence.discovery.source_verifier import (
    classify_page,
    extract_page_text,
    verify_candidate,
)


def test_extract_page_text_removes_navigation_and_scripts():
    soup = BeautifulSoup(
        """
        <html>
            <head><title>Research Opportunities</title></head>
            <body>
                <nav>Navigation text</nav>
                <script>Hidden script text</script>
                <main>Undergraduate research opportunities</main>
            </body>
        </html>
        """,
        "html.parser",
    )

    text = extract_page_text(soup)

    assert "Undergraduate research opportunities" in text
    assert "Navigation text" not in text
    assert "Hidden script text" not in text


def test_classify_university_research_page():
    result = classify_page(
        title="Undergraduate Research Opportunities",
        url="https://example.edu/research",
        page_text=(
            "Explore undergraduate research opportunities. "
            "Find summer research programs and research internships."
        ),
    )

    assert result["classification"] == "verified_source_candidate"
    assert "program" in result["source_types"]


def test_classify_informational_article():
    result = classify_page(
        title="How to Pursue Undergraduate Research",
        url="https://example.com/blog/research-guide",
        page_text=(
            "A guide to finding research opportunities. "
            "Read our advice on contacting professors."
        ),
    )

    assert result["classification"] == "not_source"
    assert result["negative_signals"]


def test_classify_unclear_page():
    result = classify_page(
        title="Student Resources",
        url="https://example.edu/students/resources",
        page_text="Information for students at the university.",
    )

    assert result["classification"] == "needs_review"


def test_verify_candidate_records_page_evidence():
    def fake_fetcher(url):
        soup = BeautifulSoup(
            """
            <html>
                <head>
                    <title>Summer Research Program</title>
                </head>
                <body>
                    Undergraduate research program.
                    Apply for summer research opportunities.
                </body>
            </html>
            """,
            "html.parser",
        )

        return FetchResult(
            soup=soup,
            status_code=200,
            error=None,
        )

    candidate = {
        "name": "Summer Research",
        "url": "https://example.edu/research",
        "status": "pending",
        "enabled": False,
    }

    result = verify_candidate(candidate, fetcher=fake_fetcher)

    assert result["page_verification"]["status"] == "completed"
    assert (
        result["page_verification"]["classification"]
        == "verified_source_candidate"
    )
    assert result["status"] == "pending"
    assert result["enabled"] is False


def test_verify_candidate_records_inaccessible_page():
    def fake_fetcher(url):
        return FetchResult(
            soup=None,
            status_code=403,
            error="Access denied",
        )

    candidate = {
        "name": "Example",
        "url": "https://example.edu/research",
        "status": "pending",
        "enabled": False,
    }

    result = verify_candidate(candidate, fetcher=fake_fetcher)

    assert result["page_verification"]["status"] == "inaccessible"
    assert result["page_verification"]["http_status"] == 403
    assert result["status"] == "pending"

def test_blog_article_rejected_despite_positive_keywords():
    result = classify_page(
        title="How To Pursue Undergraduate Research Opportunities",
        url="https://example.com/blog/research-opportunities",
        page_text=(
            "Explore undergraduate research opportunities, "
            "research internships, and research assistant positions."
        ),
    )

    assert result["classification"] == "not_source"


def test_inaccessible_candidate_requires_review():
    def fake_fetcher(url):
        return FetchResult(
            soup=None,
            status_code=403,
            error="Access denied",
        )

    candidate = {
        "name": "Example",
        "url": "https://example.com/research",
        "status": "pending",
        "enabled": False,
    }

    result = verify_candidate(candidate, fetcher=fake_fetcher)

    verification = result["page_verification"]

    assert verification["status"] == "inaccessible"
    assert verification["classification"] == "needs_review"