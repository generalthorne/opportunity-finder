
"""Retrieve and extract the contents of prioritized opportunity pages."""

import json
import logging
import time

from datetime import datetime, timezone
from pathlib import Path

from opportunity_intelligence.collectors.web_collector import fetch_page
from opportunity_intelligence.investigation.page_cache import PageCache

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "prioritized_links.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "raw" / "investigated_pages.json"
)

MAX_INVESTIGATION_ATTEMPTS = 3

# These errors are generally temporary and worth retrying.
TRANSIENT_HTTP_ERRORS = {408, 425, 429}


def is_retryable_failure(status_code: int | None) -> bool:
    """Determine whether a failed HTTP request is worth retrying."""

    if status_code is None:
        return True

    if status_code in TRANSIENT_HTTP_ERRORS:
        return True

    if 400 <= status_code < 500:
        return False

    return True


def investigate_page(
    link: dict,
    cache: PageCache | None = None,
) -> dict:
    """Retrieve one prioritized page, reusing cached content when possible."""

    url = link["url"]

    record = {
        "url": url,
        "text": link.get("text"),
        "link_type": link.get("link_type"),
        "relevance_score": link.get("relevance_score"),
        "matched_keywords": link.get("matched_keywords", []),
        "discovered_in": link.get("discovered_in", []),
        "investigated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "http_status_code": None,
        "error": None,
        "page_title": None,
        "page_text": None,
        "cache_status": "not_cached",
        "investigation_attempts": 1,
        "retryable": True,
    }

    cached_entry = cache.get(url) if cache is not None else None

    conditional_headers = (
        cache.get_conditional_headers(cached_entry)
        if cache is not None and cached_entry is not None
        else None
    )

    result = (
        fetch_page(url, conditional_headers=conditional_headers)
        if conditional_headers
        else fetch_page(url)
    )

    record["http_status_code"] = result.status_code
    record["error"] = result.error

    if result.not_modified:
        if cached_entry is None:
            result = fetch_page(url)

            record["http_status_code"] = result.status_code
            record["error"] = result.error

        else:
            record["status"] = "success"
            record["page_title"] = cached_entry["page_title"]
            record["page_text"] = cached_entry["page_text"]
            record["cache_status"] = "revalidated"
            record["retryable"] = False

            cache.revalidated += 1
            cache.mark_revalidated(url)

            return record

    if result.soup is None:
        record["retryable"] = is_retryable_failure(
            result.status_code
        )
        return record

    soup = result.soup

    page_title = (
        soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    page_text = soup.get_text(
        separator="\n",
        strip=True,
    )

    record["status"] = "success"
    record["page_title"] = page_title
    record["page_text"] = page_text
    record["cache_status"] = "downloaded"
    record["retryable"] = False

    if cache is not None:
        cache.downloads += 1
        cache.set(
            url=url,
            page_title=page_title,
            page_text=page_text,
            status_code=result.status_code or 200,
            headers=result.headers,
        )

    return record


def save_investigation_results(
    results: list[dict],
    output_file: Path = OUTPUT_FILE,
) -> None:
    """Save all accumulated investigation results."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "investigated_at": datetime.now(timezone.utc).isoformat(),
        "total_pages": len(results),
        "successful_pages": sum(
            result["status"] == "success"
            for result in results
        ),
        "failed_pages": sum(
            result["status"] == "failed"
            for result in results
        ),
        "pages": results,
    }

    temporary_file = output_file.with_suffix(
        output_file.suffix + ".tmp"
    )

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temporary_file.replace(output_file)


def investigate_pages(
    input_file: Path = INPUT_FILE,
    delay_seconds: float = 0.5,
    max_pages: int | None = 5,
    output_file: Path | None = None,
) -> list[dict]:
    """Investigate a limited number of pages and resume previous runs."""

    input_file = Path(input_file)

    if output_file is None:
        if input_file.resolve() == INPUT_FILE.resolve():
            output_file = OUTPUT_FILE
        else:
            output_file = input_file.with_name("investigated_pages.json")
    else:
        output_file = Path(output_file)

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    links = data.get("links", [])

    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    existing_results = []

    if output_file.exists():
        try:
            with output_file.open("r", encoding="utf-8") as file:
                previous_data = json.load(file)

            existing_results = previous_data.get("pages", [])

        except (json.JSONDecodeError, OSError):
            logger.exception(
                "Could not load previous investigation results."
            )

    results = list(existing_results)

    result_indices = {
        record["url"]: index
        for index, record in enumerate(results)
        if isinstance(record.get("url"), str)
    }

    completed_urls = {
        record["url"]
        for record in results
        if record.get("status") == "success"
        and isinstance(record.get("url"), str)
    }

    attempted_urls = set(result_indices)

    new_links = []
    failed_links = []

    for link in links:
        url = link.get("url")

        if not isinstance(url, str) or not url.strip():
            continue

        if url in completed_urls:
            continue

        if url not in attempted_urls:
            new_links.append(link)
            continue

        previous_record = results[result_indices[url]]

        if previous_record.get("status") != "failed":
            continue

        attempts = previous_record.get(
            "investigation_attempts",
            1,
        )

        try:
            attempts = int(attempts)
        except (TypeError, ValueError):
            attempts = 1

        retryable = previous_record.get("retryable")

        if retryable is None:
            retryable = is_retryable_failure(
                previous_record.get("http_status_code")
            )

        if not retryable:
            continue

        if attempts >= MAX_INVESTIGATION_ATTEMPTS:
            continue

        failed_links.append(
            (
                attempts,
                previous_record.get("investigated_at", ""),
                link,
            )
        )

    # Retry pages with fewer previous attempts first.
    # Within the same attempt count, older failures go first.
    failed_links.sort(
        key=lambda item: (item[0], item[1])
    )

    retry_links = [item[2] for item in failed_links]

    # Always prioritize never-investigated pages.
    links_to_process = new_links + retry_links

    attempt_counts = {
        item[2]["url"]: item[0] + 1
        for item in failed_links
    }

    for link in new_links:
        attempt_counts[link["url"]] = 1

    cache = PageCache()
    new_pages_attempted = 0

    logger.info("Loaded webpage cache: %s", cache.cache_file)
    logger.info("Previously investigated pages: %d", len(results))
    logger.info("Previously completed pages: %d", len(completed_urls))
    logger.info("Uninvestigated links: %d", len(new_links))
    logger.info("Retryable failed links: %d", len(retry_links))
    logger.info(
        "Permanently failed or exhausted links: %d",
        len(failed_links) - len(retry_links),
    )
    logger.info("Maximum attempts per URL: %d", MAX_INVESTIGATION_ATTEMPTS)
    logger.info("New page limit: %s", max_pages or "unlimited")

    try:
        for link in links_to_process:

            if (
                max_pages is not None
                and new_pages_attempted >= max_pages
            ):
                break

            url = link["url"]

            if new_pages_attempted > 0 and delay_seconds > 0:
                time.sleep(delay_seconds)

            new_pages_attempted += 1

            print(
                f"Investigating page "
                f"{new_pages_attempted}/"
                f"{max_pages if max_pages is not None else 'unlimited'}: "
                f"{url}"
            )

            result = investigate_page(link, cache)

            result["investigation_attempts"] = attempt_counts[url]

            if result["status"] == "failed":
                result["retryable"] = is_retryable_failure(
                    result.get("http_status_code")
                )
            else:
                result["retryable"] = False

            if url in result_indices:
                results[result_indices[url]] = result
            else:
                result_indices[url] = len(results)
                results.append(result)

            print(
                f"Status: {result['status']} "
                f"| Attempt: {result['investigation_attempts']}/"
                f"{MAX_INVESTIGATION_ATTEMPTS} "
                f"| Retryable: {result['retryable']} "
                f"| Cache: {result['cache_status']}"
            )

            save_investigation_results(
                results,
                output_file=output_file,
            )
            cache.save()

    finally:
        cache.save()

        logger.info("Webpage cache saved: %s", cache.cache_file)
        logger.info("Cached URL lookups: %d", cache.hits)
        logger.info("Cache misses: %d", cache.misses)
        logger.info("Pages revalidated: %d", cache.revalidated)
        logger.info("Pages downloaded: %d", cache.downloads)

    logger.info("New pages attempted: %d", new_pages_attempted)
    logger.info("Total accumulated pages: %d", len(results))

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    results = investigate_pages()
    save_investigation_results(results)

    print("\nInvestigation complete.")
    print(f"Total accumulated pages: {len(results)}")
    print(f"Results saved to: {OUTPUT_FILE}")
