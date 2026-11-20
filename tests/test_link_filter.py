
from opportunity_intelligence.discovery.link_filter import (
    score_link,
    classify_link,
    filter_relevant_links
)


def test_score_relevant_link():
    link = {
        "text": "Summer Research Opportunities",
        "url": "https://example.com/research"
    }

    result = score_link(link)

    assert result["relevance_score"] > 0
    assert "summer research" in result["matched_keywords"]


def test_score_irrelevant_link():
    link = {
        "text": "Contact Us",
        "url": "https://example.com/contact"
    }

    result = score_link(link)

    assert result["relevance_score"] == 0
    assert result["link_type"] == "irrelevant"


def test_classify_individual_opportunity():
    link = {
        "text": "First-Year Summer Research Fellowship",
        "url": "https://example.com/fellowship"
    }

    assert classify_link(link) == "opportunity"


def test_classify_directory():
    link = {
        "text": "Advertised Projects",
        "url": "https://example.com/projects"
    }

    assert classify_link(link) == "directory"


def test_classify_informational():
    link = {
        "text": "Applying to Research Opportunities",
        "url": "https://example.com/apply"
    }

    assert classify_link(link) == "informational"


def test_classify_irrelevant_navigation():
    link = {
        "text": "Skip to content",
        "url": "https://example.com/#content"
    }

    assert classify_link(link) == "irrelevant"


def test_filter_relevant_links():
    links = [
        {
            "text": "About Us",
            "url": "https://example.com/about"
        },
        {
            "text": "Summer Research Fellowship",
            "url": "https://example.com/fellowship"
        },
        {
            "text": "Student Internships",
            "url": "https://example.com/internships"
        }
    ]

    results = filter_relevant_links(links)

    assert len(results) == 2
    assert results[0]["relevance_score"] >= results[1]["relevance_score"]


def test_filter_minimum_score():
    links = [
        {
            "text": "Summer",
            "url": "https://example.com/summer"
        },
        {
            "text": "Internship Opportunities",
            "url": "https://example.com/internships"
        }
    ]

    results = filter_relevant_links(links, min_score=3)

    assert len(results) == 1
    assert results[0]["text"] == "Internship Opportunities"


def test_filter_empty_list():
    assert filter_relevant_links([]) == []
