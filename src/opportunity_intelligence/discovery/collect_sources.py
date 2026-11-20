
import json
import time

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import fetch_page
from opportunity_intelligence.discovery.source_registry import (
    Source,
    load_sources,
    get_enabled_sources
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"


def extract_links(soup: BeautifulSoup, base_url: str) -> list[dict]:
    """Extract unique HTTP(S) links from a webpage."""

    links = []
    seen_urls = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()

        # Resolve relative URLs using the original page URL.
        full_url = urljoin(base_url, href)

        # Ignore non-web links and duplicate URLs.
        if not full_url.startswith(("http://", "https://")):
            continue

        if full_url in seen_urls:
            continue

        seen_urls.add(full_url)

        link_text = anchor.get_text(" ", strip=True)

        links.append({
            "text": link_text,
            "url": full_url
        })

    return links



def collect_source(source: Source) -> dict:
    """Retrieve and extract the readable contents of one source."""

    fetch_result = fetch_page(str(source.url))
    soup = fetch_result.soup

    record = {
        "source_id": source.id,
        "source_name": source.name,
        "url": str(source.url),
        "region": source.region,
        "source_type": source.source_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "http_status_code": fetch_result.status_code,
        "error": fetch_result.error,
        "page_title": None,
        "page_text": None,
        "links": []
    }

    if soup is None:
        return record

    title = soup.title.get_text(strip=True) if soup.title else None
    page_text = soup.get_text(separator="\n", strip=True)
    links = extract_links(soup, str(source.url))

    record["status"] = "success"
    record["page_title"] = title
    record["page_text"] = page_text
    record["links"] = links

    return record


    title = soup.title.get_text(strip=True) if soup.title else None
    page_text = soup.get_text(separator="\n", strip=True)
    links = extract_links(soup, str(source.url))

    record["status"] = "success"
    record["page_title"] = title
    record["page_text"] = page_text
    record["links"] = links

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
        print(f"Links found: {len(record['links'])}")

    return results
