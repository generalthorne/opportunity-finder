
from opportunity_intelligence.discovery.search_providers.tavily import (
    TavilySearchProvider
)
from opportunity_intelligence.discovery.search_queries import SEARCH_QUERIES
from opportunity_intelligence.discovery.external_discovery import (
    search_for_candidates,
    merge_review_candidates
)
from opportunity_intelligence.discovery.source_discovery import (
    get_existing_source_urls,
    normalize_url
)


def main():
    provider = TavilySearchProvider()

    candidates = search_for_candidates(
        provider=provider,
        queries=SEARCH_QUERIES[:2],
        max_results=5
    )

    existing_urls = get_existing_source_urls()

    new_candidates = [
        candidate
        for candidate in candidates
        if normalize_url(candidate["url"]) not in existing_urls
    ]

    merged = merge_review_candidates(new_candidates)

    print("\nNEW CANDIDATES:", len(new_candidates))

    for candidate in new_candidates:
        print(f"\nName: {candidate['name']}")
        print(f"URL: {candidate['url']}")
        print(f"Type: {candidate['source_type']}")
        print(f"Score: {candidate['discovery_score']}")
        print(f"Region: {candidate['region']}")

    print("\nTOTAL REVIEW QUEUE:", len(merged))


if __name__ == "__main__":
    main()
