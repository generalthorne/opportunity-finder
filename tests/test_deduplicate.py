from opportunity_intelligence.extraction.deduplicate import (
    deduplicate_opportunities
)

from opportunity_intelligence.extraction.opportunity_extractor import (
    extract_pey_coop
)


def create_pey_opportunity(url: str):
    return extract_pey_coop({"url": url})


def test_deduplicate_removes_identical_opportunities():
    first = create_pey_opportunity("https://example.com/pey")
    second = create_pey_opportunity("https://example.com/pey-copy")

    results = deduplicate_opportunities([first, second])

    assert len(results) == 1


def test_deduplicate_preserves_different_opportunities():
    first = create_pey_opportunity("https://example.com/pey")
    second = first.model_copy(
        update={"title": "Different Research Program"}
    )

    results = deduplicate_opportunities([first, second])

    assert len(results) == 2


def test_deduplicate_preserves_first_occurrence():
    first = create_pey_opportunity("https://example.com/pey")
    second = create_pey_opportunity("https://example.com/pey-copy")

    results = deduplicate_opportunities([first, second])

    assert str(results[0].source_url) == str(first.source_url)



def test_deduplicate_preserves_all_source_urls():
    first = create_pey_opportunity("https://example.com/pey")
    second = create_pey_opportunity("https://example.com/pey-copy")
    third = create_pey_opportunity("https://example.com/pey-alias")

    results = deduplicate_opportunities([first, second, third])

    assert len(results) == 1
    assert len(results[0].related_source_urls) == 2

    related_urls = {
        str(url) for url in results[0].related_source_urls
    }

    assert "https://example.com/pey-copy" in related_urls
    assert "https://example.com/pey-alias" in related_urls