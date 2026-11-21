
import logging

from opportunity_intelligence.extraction.opportunity_extractor import (
    extract_opportunities,
    save_opportunities
)


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)


if __name__ == "__main__":
    opportunities = extract_opportunities(
        max_pages=1,
        model="qwen3:4b"
    )

    save_opportunities(opportunities)

    print(f"\nUnique opportunities extracted: {len(opportunities)}")
