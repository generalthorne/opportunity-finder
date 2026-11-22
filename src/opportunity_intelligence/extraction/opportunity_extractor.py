
"""Extract structured opportunities from investigated webpages."""

from pathlib import Path
import json
import logging

from opportunity_intelligence.extraction.deduplicate import (
    deduplicate_opportunities
)
from opportunity_intelligence.extraction.page_extractor import (
    extract_opportunities_from_page
)
from opportunity_intelligence.extraction.quality_report import (
    build_quality_report
)
from opportunity_intelligence.models import Opportunity
from opportunity_intelligence.storage.database import DEFAULT_DATABASE
from opportunity_intelligence.storage.repository import (
    save_opportunities as save_opportunities_to_database
)
from opportunity_intelligence.exporters.excel_exporter import (
    export_to_excel
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


def extract_opportunities(
    input_file: Path = INPUT_FILE,
    model: str | None = None,
    max_pages: int | None = None,
    quality_report_file: Path = QUALITY_REPORT_FILE
) -> list[Opportunity]:
    """Extract and deduplicate opportunities from investigated pages."""

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    pages = data.get("pages", [])

    if max_pages is not None:
        pages = pages[:max_pages]

    opportunities = []

    successful_pages = 0
    failed_pages = 0
    total_pages = len(pages)

    logger.info("Starting extraction of %d pages.", total_pages)

    for index, page in enumerate(pages, start=1):
        page_url = page.get("url", "Unknown URL")

        logger.info(
            "Processing page %d/%d: %s",
            index,
            total_pages,
            page_url
        )

        try:
            page_opportunities = extract_opportunities_from_page(
                page=page,
                model=model
            )

            opportunities.extend(page_opportunities)
            successful_pages += 1

        except Exception:
            failed_pages += 1
            logger.exception(
                "Failed to extract opportunities from %s",
                page_url
            )

    unique_opportunities = deduplicate_opportunities(opportunities)

    quality_report = build_quality_report(unique_opportunities)

    save_quality_report(
        quality_report,
        quality_report_file
    )

    logger.info("Extraction completed.")
    logger.info("Successfully processed pages: %d", successful_pages)
    logger.info("Failed pages: %d", failed_pages)
    logger.info("Opportunities extracted: %d", len(opportunities))
    logger.info(
        "Unique opportunities after deduplication: %d",
        len(unique_opportunities)
    )

    return unique_opportunities


def save_opportunities(
    opportunities: list[Opportunity],
    output_file: Path = OUTPUT_FILE
) -> None:
    """Save extracted opportunities as JSON."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_opportunities": len(opportunities),
        "opportunities": [
            opportunity.model_dump(mode="json")
            for opportunity in opportunities
        ]
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def save_quality_report(
    report: dict,
    output_file: Path = QUALITY_REPORT_FILE
) -> None:
    """Save the extraction quality report as JSON."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    opportunities = extract_opportunities()

    # Preserve the JSON output for debugging and backup.
    save_opportunities(opportunities)

    # Save or update the persistent SQLite records.
    database_result = save_opportunities_to_database(
        opportunities,
        DEFAULT_DATABASE
    )

    # Generate the user-facing workbook from the database.
    workbook_path = export_to_excel(
        database_path=DEFAULT_DATABASE
    )

    print()
    print("Extraction completed.")
    print(f"New database records: {database_result['inserted']}")
    print(f"Updated database records: {database_result['updated']}")
    print(f"Total database records: {database_result['total_processed']}")
    print(f"JSON backup: {OUTPUT_FILE}")
    print(f"Excel workbook: {workbook_path}")
    print(f"Database: {DEFAULT_DATABASE}")
