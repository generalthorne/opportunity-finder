
"""Discover, verify, and automatically register opportunity sources."""

import argparse
import json
import time

from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from opportunity_intelligence.discovery.search_providers.base import (
    SearchProvider,
)
from opportunity_intelligence.discovery.search_providers.tavily import (
    TavilySearchProvider,
)
from opportunity_intelligence.discovery.search_queries import SEARCH_QUERIES
from opportunity_intelligence.discovery.source_discovery import (
    build_candidate,
    get_existing_source_urls,
    normalize_url,
)
from opportunity_intelligence.discovery.source_registry import (
    DEFAULT_DISCOVERED_CONFIG,
    Source,
    load_sources,
)
from opportunity_intelligence.discovery.source_verifier import (
    verify_candidates,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

SEARCH_HISTORY_FILE = (
    PROJECT_ROOT / "data" / "processed" / "search_history.json"
)

VERIFIED_CLASSIFICATION = "verified_source_candidate"


def load_search_history(history_file: Path = SEARCH_HISTORY_FILE) -> dict:
    """Load persistent search execution history."""

    if not history_file.exists():
        return {"queries": {}}

    with history_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(
        data.get("queries"), dict
    ):
        raise ValueError("Invalid search history file.")

    return data


def save_search_history(
    history: dict,
    history_file: Path = SEARCH_HISTORY_FILE,
) -> None:
    """Save search history atomically."""

    history_file.parent.mkdir(parents=True, exist_ok=True)

    temporary_file = history_file.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(history, file, indent=4, ensure_ascii=False)

    temporary_file.replace(history_file)


def select_queries_to_run(
    queries: list[dict],
    history: dict,
    max_searches: int = 6,
    cooldown_days: int = 30,
    failure_retry_days: int = 1,
    force: bool = False,
    now: datetime | None = None,
) -> list[dict]:
    """Select priority queries that are due to run."""

    if max_searches < 1:
        raise ValueError("max_searches must be at least 1.")

    if cooldown_days < 0 or failure_retry_days < 0:
        raise ValueError("Cooldown periods cannot be negative.")

    current_time = now or datetime.now(timezone.utc)
    history_entries = history.get("queries", {})

    ordered_queries = sorted(
        queries,
        key=lambda query: (
            query.get("priority", 3),
            query.get("id", query["query"]),
        ),
    )

    selected = []

    for query in ordered_queries:
        query_id = query.get("id", query["query"])
        previous = history_entries.get(query_id, {})

        if not force and previous.get("last_attempted_at"):
            last_attempt = datetime.fromisoformat(
                previous["last_attempted_at"]
            )

            if last_attempt.tzinfo is None:
                last_attempt = last_attempt.replace(
                    tzinfo=timezone.utc
                )

            retry_days = (
                failure_retry_days
                if previous.get("status") == "failed"
                else cooldown_days
            )

            if current_time - last_attempt < timedelta(days=retry_days):
                continue

        selected.append(query)

        if len(selected) >= max_searches:
            break

    return selected


def search_single_query(
    provider: SearchProvider,
    search: dict,
    max_results: int = 10,
) -> tuple[list[dict], int]:
    """Run one search query and convert results into candidates."""

    query = search["query"]
    region = search["region"]

    print(f"Searching: {query}")

    results = provider.search(
        query=query,
        max_results=max_results,
    )

    candidates = {}

    for result in results:
        link = {
            "title": result.title,
            "text": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "relevance_score": round((result.score or 0) * 10),
            "matched_keywords": [],
            "link_type": "external_search",
            "discovered_in": [
                {
                    "name": "Tavily external search",
                    "region": region,
                }
            ],
            "search_query": query,
            "search_provider": "Tavily",
            "search_score": result.score,
        }

        candidate = build_candidate(link)

        if candidate is None:
            continue

        candidate["discovery_evidence"]["search_query_id"] = search.get("id")
        candidate["discovery_evidence"]["search_category"] = search.get(
            "category"
        )
        candidate["discovery_evidence"]["search_priority"] = search.get(
            "priority"
        )

        normalized_url = normalize_url(candidate["url"])

        if normalized_url not in candidates:
            candidates[normalized_url] = candidate

        elif (
            candidate["discovery_score"]
            > candidates[normalized_url]["discovery_score"]
        ):
            candidates[normalized_url] = candidate

    return list(candidates.values()), len(results)


def search_for_candidates(
    provider: SearchProvider,
    queries: list[dict] = SEARCH_QUERIES,
    max_results: int = 10,
    delay_seconds: float = 0.5,
) -> list[dict]:
    """Search multiple queries and deduplicate candidates."""

    candidates = {}

    for index, search in enumerate(queries):
        query_candidates, _ = search_single_query(
            provider=provider,
            search=search,
            max_results=max_results,
        )

        for candidate in query_candidates:
            normalized_url = normalize_url(candidate["url"])

            if normalized_url not in candidates:
                candidates[normalized_url] = candidate

            elif (
                candidate["discovery_score"]
                > candidates[normalized_url]["discovery_score"]
            ):
                candidates[normalized_url] = candidate

        if delay_seconds > 0 and index < len(queries) - 1:
            time.sleep(delay_seconds)

    return sorted(
        candidates.values(),
        key=lambda candidate: candidate["discovery_score"],
        reverse=True,
    )


def register_verified_sources(
    candidates: list[dict],
    discovered_config_path: Path = DEFAULT_DISCOVERED_CONFIG,
) -> list[Source]:
    """Register only successfully verified, non-duplicate sources."""

    existing_sources = load_sources(
        discovered_config_path=discovered_config_path
    )

    existing_ids = {
        source.id for source in existing_sources
    }

    existing_urls = {
        normalize_url(str(source.url))
        for source in existing_sources
    }

    registered = []

    for candidate in candidates:
        verification = candidate.get("page_verification", {})

        # An accessible page alone is not sufficient.
        if verification.get("status") != "completed":
            continue

        if verification.get("classification") != VERIFIED_CLASSIFICATION:
            continue

        if verification.get("score", 0) < 70:
            continue

        try:
            source = Source.model_validate({
                "id": candidate["id"],
                "name": candidate["name"],
                "url": candidate["url"],
                "region": candidate["region"],
                "source_type": candidate["source_type"],
                "categories": candidate["categories"],
                "enabled": True,
                "notes": candidate.get("notes"),
            })
        except (KeyError, ValueError):
            continue

        normalized_url = normalize_url(str(source.url))

        if source.id in existing_ids or normalized_url in existing_urls:
            continue

        registered.append(source)
        existing_ids.add(source.id)
        existing_urls.add(normalized_url)

    if not registered:
        return []

    existing_data = []

    if discovered_config_path.exists():
        with discovered_config_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = yaml.safe_load(file)

        if not isinstance(data, dict) or not isinstance(
            data.get("sources"), list
        ):
            raise ValueError("Invalid discovered source registry.")

        existing_data = data["sources"]

    existing_data.extend(
        source.model_dump(mode="json")
        for source in registered
    )

    discovered_config_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = discovered_config_path.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        yaml.safe_dump(
            {"sources": existing_data},
            file,
            sort_keys=False,
            allow_unicode=True,
        )

    temporary_file.replace(discovered_config_path)

    return registered


def run_external_discovery(
    history_file: Path = SEARCH_HISTORY_FILE,
    discovered_config_path: Path = DEFAULT_DISCOVERED_CONFIG,
    max_results: int = 10,
    max_searches: int = 6,
    cooldown_days: int = 30,
    failure_retry_days: int = 1,
    verification_limit: int = 20,
    delay_seconds: float = 0.5,
    provider: SearchProvider | None = None,
    force: bool = False,
) -> list[Source]:
    """Search, verify, and automatically register opportunity sources."""

    if max_results < 1:
        raise ValueError("max_results must be at least 1.")

    if verification_limit < 0:
        raise ValueError("verification_limit cannot be negative.")

    if delay_seconds < 0:
        raise ValueError("delay_seconds cannot be negative.")

    provider = provider or TavilySearchProvider()
    history = load_search_history(history_file)

    queries_to_run = select_queries_to_run(
        queries=SEARCH_QUERIES,
        history=history,
        max_searches=max_searches,
        cooldown_days=cooldown_days,
        failure_retry_days=failure_retry_days,
        force=force,
    )

    if not queries_to_run:
        print("No searches are due to run.")
        return []

    print(f"Searches selected: {len(queries_to_run)}")

    existing_urls = get_existing_source_urls()
    discovered_candidates = {}

    successful_searches = 0
    failed_searches = 0

    for index, search in enumerate(queries_to_run):
        query_id = search.get("id", search["query"])
        attempted_at = datetime.now(timezone.utc).isoformat()

        try:
            query_candidates, result_count = search_single_query(
                provider=provider,
                search=search,
                max_results=max_results,
            )

            query_candidates = [
                candidate
                for candidate in query_candidates
                if normalize_url(candidate["url"]) not in existing_urls
            ]

            for candidate in query_candidates:
                normalized_url = normalize_url(candidate["url"])

                if normalized_url not in discovered_candidates:
                    discovered_candidates[normalized_url] = candidate

                elif (
                    candidate["discovery_score"]
                    > discovered_candidates[normalized_url]["discovery_score"]
                ):
                    discovered_candidates[normalized_url] = candidate

            history["queries"][query_id] = {
                "query": search["query"],
                "region": search["region"],
                "category": search["category"],
                "priority": search.get("priority", 3),
                "last_attempted_at": attempted_at,
                "status": "success",
                "result_count": result_count,
                "candidate_count": len(query_candidates),
                "error": None,
            }

            successful_searches += 1

        except Exception as error:
            print(f"Search failed: {error}")

            history["queries"][query_id] = {
                "query": search["query"],
                "region": search["region"],
                "category": search["category"],
                "priority": search.get("priority", 3),
                "last_attempted_at": attempted_at,
                "status": "failed",
                "result_count": 0,
                "candidate_count": 0,
                "error": str(error),
            }

            failed_searches += 1

        # Save progress after every query.
        save_search_history(history, history_file)

        if delay_seconds > 0 and index < len(queries_to_run) - 1:
            time.sleep(delay_seconds)

    candidates = sorted(
        discovered_candidates.values(),
        key=lambda candidate: candidate["discovery_score"],
        reverse=True,
    )

    candidates_to_verify = candidates[:verification_limit]

    print(f"\nCandidates found: {len(candidates)}")
    print(f"Candidates selected for verification: {len(candidates_to_verify)}")

    verified_candidates = verify_candidates(
        candidates_to_verify,
        delay_seconds=1.0,
    )

    registered = register_verified_sources(
        verified_candidates,
        discovered_config_path,
    )

    print("\nDiscovery summary")
    print("-" * 40)
    print(f"Searches attempted: {len(queries_to_run)}")
    print(f"Successful searches: {successful_searches}")
    print(f"Failed searches: {failed_searches}")
    print(f"Candidates found: {len(candidates)}")
    print(f"Pages verified: {len(verified_candidates)}")
    print(f"Sources automatically registered: {len(registered)}")

    for source in registered:
        print(f"  + {source.name}")

    print(f"Search history saved to: {history_file}")
    print(f"Source registry updated: {discovered_config_path}")

    return registered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Discover and register verified opportunity sources."
    )

    parser.add_argument("--max-searches", type=int, default=6)
    parser.add_argument("--max-results", type=int, default=10)
    parser.add_argument("--cooldown-days", type=int, default=30)
    parser.add_argument("--failure-retry-days", type=int, default=1)
    parser.add_argument("--force", action="store_true")

    args = parser.parse_args()

    run_external_discovery(
        max_searches=args.max_searches,
        max_results=args.max_results,
        cooldown_days=args.cooldown_days,
        failure_retry_days=args.failure_retry_days,
        force=args.force,
    )
