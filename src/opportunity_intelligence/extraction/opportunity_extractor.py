
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

from opportunity_intelligence.models import Opportunity


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "investigated_pages.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "opportunities.json"
)

REVIEW_CANDIDATES_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "review_candidates.json"
)


def extract_opportunities(
    input_file: Path = INPUT_FILE,
    model: str | None = None,
    max_pages: int | None = None,
    review_candidates_file: Path = REVIEW_CANDIDATES_FILE
) -> list[Opportunity]:
    """Extract and deduplicate opportunities from investigated pages."""

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    pages = data.get("pages", [])

    if max_pages is not None:
        pages = pages[:max_pages]

    opportunities = []
    review_candidates = []

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
                model=model,
                review_candidates=review_candidates
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

    save_review_candidates(
        review_candidates,
        review_candidates_file
    )

    logger.info("Extraction completed.")
    logger.info("Successfully processed pages: %d", successful_pages)
    logger.info("Failed pages: %d", failed_pages)
    logger.info("Opportunities extracted: %d", len(opportunities))
    logger.info(
        "Unique opportunities after deduplication: %d",
        len(unique_opportunities)
    )
    logger.info(
        "Pages requiring manual review: %d",
        len(review_candidates)
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


def save_review_candidates(
    review_candidates: list[dict],
    output_file: Path = REVIEW_CANDIDATES_FILE
) -> None:
    """Save high-relevance pages that may need manual review."""

    output_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_review_candidates": len(review_candidates),
        "review_candidates": review_candidates
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    opportunities = extract_opportunities()

    save_opportunities(opportunities)

    print(f"Opportunities extracted: {len(opportunities)}")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"Review candidates saved to: {REVIEW_CANDIDATES_FILE}")
