
"""Retrieve and extract the contents of prioritized opportunity pages."""

import json
import time

from datetime import datetime, timezone
from pathlib import Path

from opportunity_intelligence.collectors.web_collector import fetch_page


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "prioritized_links.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "investigated_pages.json"
)


def investigate_page(link: dict) -> dict:
    """Retrieve one prioritized page and extract its readable contents."""

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
        "page_text": None
    }

    result = fetch_page(url)

    record["http_status_code"] = result.status_code
    record["error"] = result.error

    if result.soup is None:
        return record

    soup = result.soup

    page_title = (
        soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    page_text = soup.get_text(
        separator="\n",
        strip=True
    )

    record["status"] = "success"
    record["page_title"] = page_title
    record["page_text"] = page_text

    return record


def investigate_pages(
    input_file: Path = INPUT_FILE,
    delay_seconds: float = 1.0
) -> list[dict]:
    """Investigate all prioritized links."""

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    links = data.get("links", [])
    results = []

    for index, link in enumerate(links):
        if index > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)

        print(
            f"Investigating {index + 1}/{len(links)}: "
            f"{link['url']}"
        )

        result = investigate_page(link)
        results.append(result)

        print(f"Status: {result['status']}")

    return results


def save_investigation_results(
    results: list[dict],
    output_file: Path = OUTPUT_FILE
) -> None:
    """Save investigated pages as a JSON file."""

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
        "pages": results
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    results = investigate_pages()
    save_investigation_results(results)

    print("\nInvestigation complete.")
    print(f"Pages investigated: {len(results)}")
    print(f"Results saved to: {OUTPUT_FILE}")
