
"""Extract structured opportunities from investigated webpages."""

from pathlib import Path
import json
import logging
from urllib.parse import urlsplit, urlunsplit

from opportunity_intelligence.extraction.deduplicate import (
    deduplicate_opportunities,
)
from opportunity_intelligence.extraction.extraction_cache import (
    DEFAULT_CACHE_FILE,
    ExtractionCache,
)
from opportunity_intelligence.extraction.page_extractor import (
    extract_opportunities_from_page,
)
from opportunity_intelligence.extraction.quality_report import (
    build_quality_report,
)
from opportunity_intelligence.models import Opportunity
from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    initialize_database,
)
from opportunity_intelligence.storage.repository import (
    save_opportunities as save_opportunities_to_database,
)
from opportunity_intelligence.exporters.excel_exporter import (
    export_to_excel,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "raw" / "investigated_pages.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "opportunities.json"
)

QUALITY_REPORT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "quality_report.json"
)

WORKBOOK_FILE = (
    PROJECT_ROOT / "data" / "output" / "opportunities.xlsx"
)


def normalize_page_url(url: str) -> str:
    """Normalize a URL for duplicate-page detection."""

    parsed = urlsplit(url.strip())

    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        parsed.query,
        "",
    ))


def deduplicate_pages(pages: list[dict]) -> list[dict]:
    """Remove duplicate webpage records while retaining the best version."""

    unique_pages = []
    page_indices = {}

    for page in pages:
        url = page.get("url")

        if not isinstance(url, str) or not url.strip():
            unique_pages.append(page)
            continue

        normalized_url = normalize_page_url(url)

        if normalized_url not in page_indices:
            page_indices[normalized_url] = len(unique_pages)
            unique_pages.append(page)
            continue

        existing_index = page_indices[normalized_url]
        existing_page = unique_pages[existing_index]

        def page_quality(candidate: dict) -> tuple[int, int]:
            is_successful = candidate.get("status") == "success"
            page_text = candidate.get("page_text")

            text_length = (
                len(page_text.strip())
                if isinstance(page_text, str)
                else 0
            )

            return int(is_successful), text_length

        if page_quality(page) > page_quality(existing_page):
            unique_pages[existing_index] = page

    return unique_pages


def save_opportunities(
    opportunities: list[Opportunity],
    output_file: Path = OUTPUT_FILE,
) -> None:
    """Save extracted opportunities as JSON."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_opportunities": len(opportunities),
        "opportunities": [
            opportunity.model_dump(mode="json")
            for opportunity in opportunities
        ],
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_quality_report(
    report: dict,
    output_file: Path = QUALITY_REPORT_FILE,
) -> None:
    """Save the extraction quality report as JSON."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)


def extract_opportunities(
    input_file: Path = INPUT_FILE,
    model: str | None = None,
    max_pages: int | None = None,
    batch_size: int = 5,
    quality_report_file: Path = QUALITY_REPORT_FILE,
    cache_file: Path = DEFAULT_CACHE_FILE,
) -> list[Opportunity]:
    """Extract opportunities incrementally with persistent checkpoints."""

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    pages = deduplicate_pages(data.get("pages", []))
    cache = ExtractionCache(cache_file)

    opportunities = []

    successful_pages = 0
    failed_pages = 0
    new_pages_processed = 0
    batch_count = 0

    logger.info("Pages available: %d", len(pages))
    logger.info("Loaded extraction cache: %s", cache_file)
    logger.info("Maximum new pages per run: %s", max_pages)
    logger.info("Batch size: %d", batch_size)
    logger.info("Starting incremental extraction.")

    def save_checkpoint() -> None:
        """Persist completed extraction results."""

        unique_opportunities = deduplicate_opportunities(
            opportunities
        )

        quality_report = build_quality_report(
            unique_opportunities
        )

        save_opportunities(
            unique_opportunities,
            OUTPUT_FILE,
        )

        save_quality_report(
            quality_report,
            quality_report_file,
        )

        initialize_database(DEFAULT_DATABASE)

        database_result = save_opportunities_to_database(
            unique_opportunities,
            DEFAULT_DATABASE,
        )

        workbook_path = export_to_excel(
            output_file=WORKBOOK_FILE,
            database_path=DEFAULT_DATABASE,
        )

        logger.info(
            "Checkpoint saved. Unique opportunities: %d",
            len(unique_opportunities),
        )
        logger.info(
            "Database records inserted: %d, updated: %d",
            database_result["inserted"],
            database_result["updated"],
        )
        logger.info("Workbook updated: %s", workbook_path)

    try:
        for index, page in enumerate(pages, start=1):

            if (
                max_pages is not None
                and new_pages_processed >= max_pages
            ):
                logger.info(
                    "Reached the limit of %d new pages.",
                    max_pages,
                )
                break

            page_url = page.get("url", "Unknown URL")
            previous_cache_hits = cache.hits

            logger.info(
                "Processing page %d/%d: %s",
                index,
                len(pages),
                page_url,
            )

            try:
                page_opportunities = extract_opportunities_from_page(
                    page=page,
                    model=model,
                    cache=cache,
                )

                opportunities.extend(page_opportunities)
                successful_pages += 1

            except Exception:
                failed_pages += 1

                logger.exception(
                    "Failed to extract opportunities from %s",
                    page_url,
                )

            # Cached pages do not consume the new-page limit.
            # All other page-processing attempts count toward the batch.
            was_cache_hit = cache.hits > previous_cache_hits

            if not was_cache_hit:
                new_pages_processed += 1
                batch_count += 1

            # Persist cache progress after every page.
            cache.save()

            if batch_count >= batch_size:
                logger.info("Saving batch checkpoint.")
                save_checkpoint()
                batch_count = 0

        logger.info("Saving final checkpoint.")
        save_checkpoint()

    finally:
        cache.save()

    unique_opportunities = deduplicate_opportunities(
        opportunities
    )

    logger.info("Incremental extraction completed.")
    logger.info("New pages processed: %d", new_pages_processed)
    logger.info("Successful page processing: %d", successful_pages)
    logger.info("Failed page processing: %d", failed_pages)
    logger.info("Cache hits: %d", cache.hits)
    logger.info("Cache misses: %d", cache.misses)
    logger.info("Unique opportunities: %d", len(unique_opportunities))

    return unique_opportunities


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    opportunities = extract_opportunities()

    print()
    print("Extraction completed.")
    print(f"Opportunities: {len(opportunities)}")
    print(f"JSON backup: {OUTPUT_FILE}")
    print(f"Excel workbook: {WORKBOOK_FILE}")
    print(f"Database: {DEFAULT_DATABASE}")
