
from opportunity_intelligence.discovery.search_queries import SEARCH_QUERIES


def test_search_queries_have_unique_ids():
    ids = [item["id"] for item in SEARCH_QUERIES]

    assert len(ids) == len(set(ids))


def test_search_queries_have_unique_query_text():
    queries = [item["query"].casefold() for item in SEARCH_QUERIES]

    assert len(queries) == len(set(queries))


def test_search_queries_have_required_metadata():
    for item in SEARCH_QUERIES:
        assert item["id"]
        assert item["query"]
        assert item["region"] in {"Canada", "US", "International"}
        assert item["category"] in {
            "research",
            "internship",
            "coop",
            "university_employment",
            "government",
            "fellowship",
        }
        assert item["priority"] in {1, 2, 3}


def test_search_queries_cover_all_regions():
    regions = {item["region"] for item in SEARCH_QUERIES}

    assert regions == {"Canada", "US", "International"}


def test_search_queries_cover_major_categories():
    categories = {item["category"] for item in SEARCH_QUERIES}

    assert {
        "research",
        "internship",
        "university_employment",
        "government",
        "fellowship",
    }.issubset(categories)


def test_search_query_count():
    assert len(SEARCH_QUERIES) == 18
