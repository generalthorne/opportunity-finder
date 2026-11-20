"""Extract structured opportunities from investigated webpages."""

from pathlib import Path
import json

from opportunity_intelligence.extraction.deduplicate import (
    deduplicate_opportunities
)

from opportunity_intelligence.models import Opportunity

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


def extract_opportunities(
    input_file: Path = INPUT_FILE
) -> list[Opportunity]:
    """Extract opportunities from all investigated pages."""

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    pages = data.get("pages", [])
    opportunities = []

    # General extraction will be implemented here.

    return deduplicate_opportunities(opportunities)


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


if __name__ == "__main__":
    opportunities = extract_opportunities()
    save_opportunities(opportunities)

    print(f"Opportunities extracted: {len(opportunities)}")
    print(f"Results saved to: {OUTPUT_FILE}")