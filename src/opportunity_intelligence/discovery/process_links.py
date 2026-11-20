
"""Process collected source links into a prioritized dataset."""

import json

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag

from opportunity_intelligence.discovery.link_filter import (
    filter_relevant_links
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_FILE = PROCESSED_DATA_DIR / "prioritized_links.json"


def normalize_url(url: str) -> str:
    """Normalize a URL for duplicate detection."""

    url_without_fragment = urldefrag(url).url

    return url_without_fragment.rstrip("/")


def process_raw_records(
    raw_dir: Path = RAW_DATA_DIR,
    min_score: int = 2
) -> list[dict]:
    """Load raw records, filter their links, and remove duplicates."""

    prioritized_links = {}

    for file_path in raw_dir.glob("*.json"):
        with file_path.open("r", encoding="utf-8") as file:
            record = json.load(file)

        if record.get("status") != "success":
            continue

        links = record.get("links", [])

        relevant_links = filter_relevant_links(
            links,
            min_score=min_score
        )

        for link in relevant_links:
            url = link["url"]
            normalized_url = normalize_url(url)

            source_information = {
                "source_id": record["source_id"],
                "source_name": record["source_name"],
                "source_url": record["url"],
                "region": record["region"],
                "source_type": record["source_type"]
            }

            if normalized_url in prioritized_links:
                existing_sources = prioritized_links[
                    normalized_url
                ]["discovered_in"]

                if source_information not in existing_sources:
                    existing_sources.append(source_information)

                continue

            prioritized_links[normalized_url] = {
                **link,
                "discovered_in": [source_information]
            }

    results = list(prioritized_links.values())

    return sorted(
        results,
        key=lambda link: link["relevance_score"],
        reverse=True
    )


def save_prioritized_links(
    links: list[dict],
    output_file: Path = OUTPUT_FILE
) -> None:
    """Save prioritized links as a JSON file."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    output_data = {
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "total_links": len(links),
        "links": links
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            output_data,
            file,
            indent=4,
            ensure_ascii=False
        )


def process_links(
    raw_dir: Path = RAW_DATA_DIR,
    output_file: Path = OUTPUT_FILE,
    min_score: int = 2
) -> list[dict]:
    """Process raw source records and save prioritized links."""

    links = process_raw_records(
        raw_dir=raw_dir,
        min_score=min_score
    )

    save_prioritized_links(links, output_file)

    print(f"Prioritized links: {len(links)}")
    print(f"Saved to: {output_file}")

    return links


if __name__ == "__main__":
    process_links()
