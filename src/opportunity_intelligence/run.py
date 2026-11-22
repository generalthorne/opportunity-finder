
"""Run the complete Opportunity Intelligence System."""

import argparse
import json
import logging
import tempfile

from pathlib import Path

from opportunity_intelligence.discovery.external_discovery import (
    run_external_discovery,
)
from opportunity_intelligence.discovery.source_registry import (
    load_sources,
    get_enabled_sources,
)
from opportunity_intelligence.discovery.collect_sources import (
    collect_sources,
)
from opportunity_intelligence.discovery.process_links import (
    process_links,
)
from opportunity_intelligence.discovery.page_investigator import (
    investigate_pages,
    save_investigation_results,
)
from opportunity_intelligence.extraction.opportunity_extractor import (
    extract_opportunities,
    save_opportunities,
)
from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    initialize_database,
)
from opportunity_intelligence.storage.repository import (
    save_opportunities as save_opportunities_to_database,
    count_opportunities,
)
from opportunity_intelligence.exporters.excel_exporter import (
    export_to_excel,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

PRIORITIZED_LINKS_FILE = (
    PROCESSED_DATA_DIR / "prioritized_links.json"
)

INVESTIGATED_PAGES_FILE = (
    RAW_DATA_DIR / "investigated_pages.json"
)

OPPORTUNITIES_FILE = (
    PROCESSED_DATA_DIR / "opportunities.json"
)

WORKBOOK_FILE = (
    PROJECT_ROOT / "data" / "output" / "opportunities.xlsx"
)

logger = logging.getLogger(__name__)


def run_pipeline(
    skip_discovery: bool = False,
    resume: bool = False,
    max_pages: int = 5,
    batch_size: int = 5,
) -> dict:
    """Execute the opportunity pipeline, optionally resuming existing work."""

    if max_pages < 1:
        raise ValueError("max_pages must be at least 1.")

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")

    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 60)
    print("OPPORTUNITY INTELLIGENCE SYSTEM")
    print("=" * 60)

    sources = get_enabled_sources(load_sources())

    successful_sources = None

    # Resume mode reuses the existing prioritized links.
    if resume:
        print("\nRESUME MODE")
        print("Skipping source discovery, collection, and link prioritization.")

        if not PRIORITIZED_LINKS_FILE.exists():
            raise FileNotFoundError(
                "Cannot resume because prioritized_links.json does not "
                "exist. Run the system once without --resume first."
            )

        with PRIORITIZED_LINKS_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            prioritized_data = json.load(file)

        prioritized_links = prioritized_data.get("links", [])

        print(f"Existing prioritized links: {len(prioritized_links)}")

    else:
        # 1. External source discovery
        print("\n[1/8] Discovering new sources...")

        if skip_discovery:
            print("External discovery skipped.")
        else:
            try:
                newly_registered = run_external_discovery()
                print(f"New sources registered: {len(newly_registered)}")
            except Exception:
                logger.exception(
                    "External discovery failed. Continuing with "
                    "the existing source registry."
                )

        # 2. Load enabled sources
        print("\n[2/8] Loading source registry...")
        print(f"Enabled sources: {len(sources)}")

        if not sources:
            raise RuntimeError(
                "No enabled sources are available. "
                "Check config/sources.yaml and discovered_sources.yaml."
            )

        # 3. Collect source pages
        print("\n[3/8] Collecting source pages...")

        with tempfile.TemporaryDirectory(
            prefix="opportunity_run_",
            dir=PROCESSED_DATA_DIR,
        ) as temporary_directory:

            collection_directory = Path(temporary_directory)

            collection_results = collect_sources(
                sources=sources,
                output_dir=collection_directory,
            )

            successful_sources = sum(
                record["status"] == "success"
                for record in collection_results
            )

            print(
                f"Successfully collected: {successful_sources}/"
                f"{len(collection_results)}"
            )

            # 4. Filter and prioritize links
            print("\n[4/8] Filtering and prioritizing links...")

            prioritized_links = process_links(
                raw_dir=collection_directory,
                output_file=PRIORITIZED_LINKS_FILE,
            )

            print(
                f"Prioritized links discovered: {len(prioritized_links)}"
            )

    # 5. Investigate a limited number of new pages
    print("\n[5/8] Investigating opportunity pages...")
    print(f"New page limit: {max_pages}")

    previous_investigation_times = {}

    if INVESTIGATED_PAGES_FILE.exists():
        try:
            with INVESTIGATED_PAGES_FILE.open(
                "r",
                encoding="utf-8",
            ) as file:
                previous_data = json.load(file)

            previous_investigation_times = {
                page["url"]: page.get("investigated_at")
                for page in previous_data.get("pages", [])
                if isinstance(page.get("url"), str)
            }

        except (json.JSONDecodeError, OSError):
            logger.exception(
                "Could not read previous investigation results."
            )

    investigation_results = investigate_pages(
        input_file=PRIORITIZED_LINKS_FILE,
        max_pages=max_pages,
    )

    save_investigation_results(
        investigation_results,
        output_file=INVESTIGATED_PAGES_FILE,
    )

    new_pages_investigated = sum(
        page.get("investigated_at")
        != previous_investigation_times.get(page.get("url"))
        for page in investigation_results
    )

    successful_pages = sum(
        page["status"] == "success"
        for page in investigation_results
    )

    print(f"New pages attempted: {new_pages_investigated}")
    print(f"Total accumulated pages: {len(investigation_results)}")
    print(f"Successfully investigated: {successful_pages}")

    # 6. Extract opportunities with a strict new-LLM-attempt limit
    print("\n[6/8] Extracting opportunities with Ollama...")
    print(f"Maximum new extraction attempts: {max_pages}")
    print(f"Extraction checkpoint size: {batch_size}")

    opportunities = extract_opportunities(
        input_file=INVESTIGATED_PAGES_FILE,
        max_pages=max_pages,
        batch_size=batch_size,
    )

    save_opportunities(
        opportunities,
        output_file=OPPORTUNITIES_FILE,
    )

    print(f"Unique opportunities in this extraction pass: {len(opportunities)}")

    # 7. Update SQLite
    print("\n[7/8] Updating opportunity database...")

    initialize_database(DEFAULT_DATABASE)

    database_result = save_opportunities_to_database(
        opportunities,
        DEFAULT_DATABASE,
    )

    print(f"New records: {database_result['inserted']}")
    print(f"Updated records: {database_result['updated']}")
    print(f"Total processed: {database_result['total_processed']}")

    # 8. Export the existing Excel workbook
    print("\n[8/8] Generating Excel workbook...")

    workbook_path = export_to_excel(
        output_file=WORKBOOK_FILE,
        database_path=DEFAULT_DATABASE,
    )

    summary = {
        "resume_mode": resume,
        "sources": len(sources),
        "successful_sources": successful_sources,
        "prioritized_links": len(prioritized_links),
        "new_pages_investigated": new_pages_investigated,
        "total_investigated_pages": len(investigation_results),
        "successful_pages": successful_pages,
        "extracted_opportunities_this_pass": len(opportunities),
        "inserted": database_result["inserted"],
        "updated": database_result["updated"],
        "total_database_records": count_opportunities(DEFAULT_DATABASE),
        "workbook": workbook_path,
        "database": DEFAULT_DATABASE,
    }

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED")
    print("=" * 60)

    for key, value in summary.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Opportunity Intelligence System."
    )

    parser.add_argument(
        "--skip-discovery",
        action="store_true",
        help="Use existing sources without running external searches.",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse existing prioritized links and skip source collection.",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum new pages to investigate and extract per run.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of new extraction attempts between checkpoints.",
    )

    args = parser.parse_args()

    if args.max_pages < 1:
        parser.error("--max-pages must be at least 1.")

    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1.")

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    run_pipeline(
        skip_discovery=args.skip_discovery,
        resume=args.resume,
        max_pages=args.max_pages,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
