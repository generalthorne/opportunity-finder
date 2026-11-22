
import json

from opportunity_intelligence.discovery.source_discovery import (
    build_candidate,
    discover_source_candidates,
    normalize_url,
    save_source_candidates
)


def test_normalize_url():
    assert normalize_url(
        "https://example.com/research/#programs"
    ) == "https://example.com/research"


def test_build_directory_candidate():
    link = {
        "text": "Undergraduate Research Opportunities Directory",
        "url": "https://example.com/research",
        "relevance_score": 10,
        "matched_keywords": ["research opportunities"],
        "link_type": "directory",
        "discovered_in": [
            {"region": "Canada"}
        ]
    }

    candidate = build_candidate(link)

    assert candidate is not None
    assert candidate["source_type"] == "directory"
    assert "research" in candidate["categories"]
    assert candidate["enabled"] is False
    assert candidate["status"] == "pending"


def test_reject_individual_opportunity():
    link = {
        "text": "Research Assistant Position - Apply Now",
        "url": "https://example.com/position",
        "relevance_score": 10,
        "link_type": "opportunity"
    }

    assert build_candidate(link) is None


def test_reject_informational_page():
    link = {
        "text": "How to Apply for Research Opportunities",
        "url": "https://example.com/apply",
        "relevance_score": 10,
        "link_type": "informational"
    }

    assert build_candidate(link) is None


def test_discover_candidates_deduplicates_urls(tmp_path):
    input_file = tmp_path / "links.json"

    links = [
        {
            "text": "Undergraduate Research Opportunities Directory",
            "url": "https://example.com/research/",
            "relevance_score": 10,
            "matched_keywords": ["research opportunities"],
            "link_type": "directory",
            "discovered_in": [{"region": "Canada"}]
        },
        {
            "text": "Research Opportunities Directory",
            "url": "https://example.com/research",
            "relevance_score": 8,
            "matched_keywords": ["research"],
            "link_type": "directory",
            "discovered_in": [{"region": "Canada"}]
        }
    ]

    input_file.write_text(
        json.dumps({"links": links}),
        encoding="utf-8"
    )

    candidates = discover_source_candidates(
        input_file=input_file,
        existing_urls=set()
    )

    assert len(candidates) == 1


def test_discover_candidates_excludes_existing_sources(tmp_path):
    input_file = tmp_path / "links.json"

    links = [{
        "text": "Undergraduate Research Opportunities Directory",
        "url": "https://example.com/research",
        "relevance_score": 10,
        "matched_keywords": ["research opportunities"],
        "link_type": "directory",
        "discovered_in": [{"region": "Canada"}]
    }]

    input_file.write_text(
        json.dumps({"links": links}),
        encoding="utf-8"
    )

    candidates = discover_source_candidates(
        input_file=input_file,
        existing_urls={"https://example.com/research/"}
    )

    assert candidates == []


def test_save_source_candidates(tmp_path):
    output_file = tmp_path / "candidates.json"

    save_source_candidates(
        [{"id": "example", "status": "pending"}],
        output_file
    )

    saved = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert saved["total_candidates"] == 1
    assert saved["candidates"][0]["status"] == "pending"



def test_rejects_informational_undergraduate_research_page():
    link = {
        "text": "Shaping Equitable and Inclusive Undergraduate Research Opportunities",
        "url": "https://example.com/research",
        "relevance_score": 15,
        "link_type": "directory"
    }

    assert build_candidate(link) is None


def test_rejects_faculty_facing_research_page():
    link = {
        "text": "Working with Undergraduate Researchers",
        "url": "https://example.com/research",
        "relevance_score": 10,
        "link_type": "other"
    }

    assert build_candidate(link) is None


def test_accepts_research_explorer():
    link = {
        "text": "Undergraduate Research Explorer",
        "url": "https://example.com/explorer",
        "relevance_score": 10,
        "link_type": "directory",
        "discovered_in": [{"region": "Canada"}]
    }

    candidate = build_candidate(link)

    assert candidate is not None
    assert candidate["source_type"] == "directory"


def test_accepts_reu_directory_search():
    link = {
        "text": "Search the Directory of REU Sites",
        "url": "https://example.com/reu/search",
        "relevance_score": 8,
        "link_type": "directory",
        "discovered_in": [{"region": "United States"}]
    }

    candidate = build_candidate(link)

    assert candidate is not None
    assert candidate["source_type"] == "directory"


def test_rejects_how_to_article():
    link = {
        "title": "How To Pursue Undergraduate Research Opportunities in Canada",
        "url": "https://example.com/blog/research-opportunities",
        "relevance_score": 10,
        "link_type": "directory"
    }

    assert build_candidate(link) is None


def test_rejects_question_and_discussion_pages():
    link = {
        "title": "What are some international undergraduate research opportunities?",
        "url": "https://example.com/research-opportunities",
        "relevance_score": 10,
        "link_type": "directory"
    }

    assert build_candidate(link) is None


def test_accepts_university_research_opportunity_page():
    link = {
        "title": "Undergraduate Research Opportunities",
        "url": "https://example.edu/current-undergraduates/research-opportunities",
        "relevance_score": 10,
        "link_type": "directory",
        "discovered_in": [{"region": "Canada"}]
    }

    candidate = build_candidate(link)

    assert candidate is not None
    assert candidate["source_type"] == "program"
    assert "research" in candidate["categories"]
