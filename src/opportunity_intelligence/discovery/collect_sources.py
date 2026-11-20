
import json
import time

from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import fetch_page
from opportunity_intelligence.discovery.source_registry import (
    Source,
    load_sources,
    get_enabled_sources
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def collect_source(source: Source) -> dict:
    """Retrieve and extract the readable contents of one source."""

    soup = fetch_page(str(source.url))

    record = {
        "source_id": source.id,
        "source_name": source.name,
        "url": str(source.url),
        "region": source.region,
        "source_type": source.source_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "page_title": None,
        "page_text": None
    }

    if soup is None:
        return record

    title = soup.title.get_text(strip=True) if soup.title else None

    page_text = soup.get_text(separator="\n", strip=True)

    record["status"] = "success"
    record["page_title"] = title
    record["page_text"] = page_text

    return record


def save_record(record: dict, output_dir: Path = RAW_DATA_DIR) -> None:
    """Save a collected source record as a JSON file."""

    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{record['source_id']}.json"
    output_path = output_dir / filename

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(record, file, indent=4, ensure_ascii=False)


def collect_sources(
    sources: list[Source] | None = None,
    output_dir: Path = RAW_DATA_DIR,
    delay_seconds: float = 1.0
) -> list[dict]:
    """Collect and save all enabled opportunity sources."""

    if sources is None:
        sources = load_sources()

    enabled_sources = get_enabled_sources(sources)

    results = []

    for index, source in enumerate(enabled_sources):
        if index > 0 and delay_seconds > 0:
            time.sleep(delay_seconds)

        print(f"Collecting: {source.name}")

        record = collect_source(source)

        save_record(record, output_dir)

        results.append(record)

        print(f"Status: {record['status']}")

    return results
