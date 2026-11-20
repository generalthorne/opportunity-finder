
from opportunity_intelligence.extraction.deduplicate import (
    deduplicate_opportunities
)

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory
)


def create_opportunity(
    url: str,
    title: str = "Undergraduate Research Assistant",
    organization: str = "Example University"
) -> Opportunity:
    """Create a generic opportunity for testing."""
    return Opportunity(
        title=title,
        organization=organization,
        category=OpportunityCategory.RESEARCH,
        source_url=url
    )


def test_deduplicate_removes_identical_opportunities():
    first = create_opportunity("https://example.com/research")
    second = create_opportunity("https://example.com/research-copy")

    results = deduplicate_opportunities([first, second])

    assert len(results) == 1


def test_deduplicate_preserves_different_opportunities():
    first = create_opportunity("https://example.com/research")
    second = create_opportunity(
        "https://example.com/other",
        title="Different Research Program"
    )

    results = deduplicate_opportunities([first, second])

    assert len(results) == 2


def test_deduplicate_preserves_first_occurrence():
    first = create_opportunity("https://example.com/research")
    second = create_opportunity("https://example.com/research-copy")

    results = deduplicate_opportunities([first, second])

    assert str(results[0].source_url) == str(first.source_url)


def test_deduplicate_preserves_all_source_urls():
    first = create_opportunity("https://example.com/research")
    second = create_opportunity("https://example.com/research-copy")
    third = create_opportunity("https://example.com/research-alias")

    results = deduplicate_opportunities([first, second, third])

    assert len(results) == 1
    assert len(results[0].related_source_urls) == 2

    related_urls = {
        str(url) for url in results[0].related_source_urls
    }

    assert "https://example.com/research-copy" in related_urls
    assert "https://example.com/research-alias" in related_urls
