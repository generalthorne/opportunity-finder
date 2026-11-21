
"""Verify stored opportunities against their original webpages."""

import logging
import time

from datetime import datetime, timezone
from typing import Callable

from opportunity_intelligence.collectors.web_collector import fetch_page
from opportunity_intelligence.extraction.page_extractor import (
    extract_opportunities_from_page
)
from opportunity_intelligence.models import Opportunity
from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    get_connection,
    initialize_database
)
from opportunity_intelligence.storage.repository import (
    get_opportunity_by_id,
    save_opportunities
)
from opportunity_intelligence.storage.verification import (
    record_verification
)


logger = logging.getLogger(__name__)


TRACKED_FIELDS = [
    "opportunity_type",
    "field",
    "location",
    "work_mode",
    "description",
    "requirements",
    "preferred_skills",
    "compensation",
    "duration",
    "start_date",
    "deadline",
    "start_date_text",
    "deadline_text",
    "eligibility",
    "application_url",
    "evidence"
]


def normalize_text(value: str | None) -> str:
    """Normalize text for conservative opportunity matching."""

    if not value:
        return ""

    return " ".join(value.casefold().split())


def opportunities_match(
    stored: Opportunity,
    extracted: Opportunity,
    extraction_count: int
) -> bool:
    """Determine whether an extracted record matches a stored record."""

    # Category and organization must always match.
    if stored.category != extracted.category:
        return False

    stored_organization = normalize_text(stored.organization)
    extracted_organization = normalize_text(extracted.organization)

    if stored_organization != extracted_organization:
        return False

    stored_title = normalize_text(stored.title)
    extracted_title = normalize_text(extracted.title)

    # Exact identity is the strongest match.
    if stored_title == extracted_title:
        return True

    # Only allow a small title variation when the page contains
    # exactly one opportunity and the organization/category match.
    if extraction_count == 1:
        from difflib import SequenceMatcher

        title_similarity = SequenceMatcher(
            None,
            stored_title,
            extracted_title
        ).ratio()

        return title_similarity >= 0.90

    # On multi-opportunity pages, require exact title matching.
    return False


def find_matching_opportunity(
    stored: Opportunity,
    extracted_opportunities: list[Opportunity]
) -> Opportunity | None:
    """Find the extracted record corresponding to a stored opportunity."""

    matches = [
        extracted
        for extracted in extracted_opportunities
        if opportunities_match(
            stored,
            extracted,
            len(extracted_opportunities)
        )
    ]

    if len(matches) != 1:
        return None

    return matches[0]


def comparable_value(value):
    """Convert values into a consistent form for change detection."""

    if hasattr(value, "isoformat"):
        return value.isoformat()

    if isinstance(value, list):
        return {
            str(item).casefold().strip()
            for item in value
        }

    if value is None:
        return None

    if hasattr(value, "value"):
        return value.value

    return str(value).strip()


def detect_changes(
    stored: Opportunity,
    extracted: Opportunity
) -> tuple[list[str], dict, dict]:
    """Compare tracked fields and return detected changes."""

    changed_fields = []
    previous_values = {}
    current_values = {}

    for field in TRACKED_FIELDS:
        old_value = getattr(stored, field)
        new_value = getattr(extracted, field)

        # Empty extraction results are not evidence that existing
        # information should be deleted.
        if new_value is None or new_value == "" or new_value == []:
            continue

        old_comparable = comparable_value(old_value)
        new_comparable = comparable_value(new_value)

        if old_comparable != new_comparable:
            changed_fields.append(field)

            # Sets must be converted to lists before JSON serialization.
            previous_values[field] = (
                sorted(old_comparable)
                if isinstance(old_comparable, set)
                else old_comparable
            )

            current_values[field] = (
                sorted(new_comparable)
                if isinstance(new_comparable, set)
                else new_comparable
            )

    return changed_fields, previous_values, current_values


def build_updated_opportunity(
    stored: Opportunity,
    extracted: Opportunity,
    checked_at: datetime
) -> Opportunity:
    """Merge extracted information into the stored opportunity."""

    updates = {}

    for field in TRACKED_FIELDS:
        new_value = getattr(extracted, field)

        if new_value is None or new_value == "" or new_value == []:
            continue

        if field in {
            "field",
            "requirements",
            "preferred_skills",
            "evidence"
        }:
            # Preserve existing values while adding newly extracted ones.
            combined = list(getattr(stored, field))

            for value in new_value:
                if value not in combined:
                    combined.append(value)

            updates[field] = combined
        else:
            updates[field] = new_value

    updates["last_verified"] = checked_at

    return stored.model_copy(update=updates)


def get_source_url(
    opportunity_id: int,
    database_path=DEFAULT_DATABASE
) -> str | None:
    """Retrieve the original source URL for a stored opportunity."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT source_url
            FROM opportunities
            WHERE id = ?
            """,
            (opportunity_id,)
        ).fetchone()

    return row["source_url"] if row else None


def verify_opportunity(
    opportunity_id: int,
    model: str | None = None,
    database_path=DEFAULT_DATABASE,
    fetcher: Callable = fetch_page,
    extractor: Callable = extract_opportunities_from_page
) -> dict:
    """Fetch, extract, compare, and update one stored opportunity."""

    checked_at = datetime.now(timezone.utc)

    stored = get_opportunity_by_id(
        opportunity_id,
        database_path
    )

    if stored is None:
        raise ValueError(
            f"Opportunity {opportunity_id} does not exist."
        )

    source_url = get_source_url(
        opportunity_id,
        database_path
    )

    try:
        fetch_result = fetcher(source_url)

    except Exception as error:
        logger.exception(
            "Page retrieval failed for opportunity %s",
            opportunity_id
        )

        record_verification(
            opportunity_id=opportunity_id,
            outcome="failed",
            source_url=source_url,
            notes=f"Page retrieval raised an exception: {error}",
            checked_at=checked_at,
            database_path=database_path
        )

        return {
            "opportunity_id": opportunity_id,
            "outcome": "failed",
            "changed_fields": []
        }

    if fetch_result.soup is None:
        if fetch_result.status_code == 404:
            outcome = "not_found"
        elif fetch_result.status_code is None:
            outcome = "failed"
        else:
            outcome = "inaccessible"

        record_verification(
            opportunity_id=opportunity_id,
            outcome=outcome,
            source_url=source_url,
            notes=fetch_result.error,
            checked_at=checked_at,
            database_path=database_path
        )

        return {
            "opportunity_id": opportunity_id,
            "outcome": outcome,
            "changed_fields": []
        }

    soup = fetch_result.soup

    page_title = (
        soup.title.get_text(strip=True)
        if soup.title
        else None
    )

    page_text = soup.get_text(
        separator="\n",
        strip=True
    )

    # An accessible but empty page cannot establish whether the
    # opportunity still exists. Record a failed check instead.
    if not page_text.strip():
        record_verification(
            opportunity_id=opportunity_id,
            outcome="failed",
            source_url=source_url,
            notes="The accessible source page contained no readable text.",
            checked_at=checked_at,
            database_path=database_path
        )

        return {
            "opportunity_id": opportunity_id,
            "outcome": "failed",
            "changed_fields": []
        }

    page = {
        "url": source_url,
        "page_title": page_title,
        "page_text": page_text,
        "status": "success",
        "http_status": fetch_result.status_code,
        "relevance_score": 10,
        "link_type": "opportunity",
        "matched_keywords": [],
        "discovered_in": []
    }

    try:
        extracted_opportunities = extractor(
            page=page,
            model=model
        )

    except Exception as error:
        logger.exception(
            "Extraction failed for opportunity %s",
            opportunity_id
        )

        record_verification(
            opportunity_id=opportunity_id,
            outcome="failed",
            source_url=source_url,
            notes=f"Opportunity extraction failed: {error}",
            checked_at=checked_at,
            database_path=database_path
        )

        return {
            "opportunity_id": opportunity_id,
            "outcome": "failed",
            "changed_fields": []
        }

    extracted = find_matching_opportunity(
        stored,
        extracted_opportunities
    )

    if extracted is None:
        record_verification(
            opportunity_id=opportunity_id,
            outcome="not_found",
            source_url=source_url,
            notes=(
                "No unambiguous matching opportunity was extracted "
                "from the accessible source page."
            ),
            checked_at=checked_at,
            database_path=database_path
        )

        return {
            "opportunity_id": opportunity_id,
            "outcome": "not_found",
            "changed_fields": []
        }

    changed_fields, previous_values, current_values = (
        detect_changes(stored, extracted)
    )

    updated_opportunity = build_updated_opportunity(
        stored,
        extracted,
        checked_at
    )

    save_opportunities(
        [updated_opportunity],
        database_path
    )

    outcome = "changed" if changed_fields else "verified"

    record_verification(
        opportunity_id=opportunity_id,
        outcome=outcome,
        changed_fields=changed_fields,
        previous_values=previous_values,
        current_values=current_values,
        source_url=source_url,
        notes=(
            "Opportunity details were updated."
            if changed_fields
            else "No changes detected in tracked fields."
        ),
        checked_at=checked_at,
        database_path=database_path
    )

    return {
        "opportunity_id": opportunity_id,
        "outcome": outcome,
        "changed_fields": changed_fields
    }


def verify_all_opportunities(
    limit: int | None = None,
    model: str | None = None,
    delay_seconds: float = 1.0,
    database_path=DEFAULT_DATABASE,
    fetcher: Callable = fetch_page,
    extractor: Callable = extract_opportunities_from_page
) -> dict:
    """Verify stored opportunities in a controlled batch."""

    if limit is not None and limit < 1:
        raise ValueError("Limit must be at least 1.")

    if delay_seconds < 0:
        raise ValueError("Delay cannot be negative.")

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT id
            FROM opportunities
            ORDER BY
                CASE WHEN last_verified IS NULL THEN 0 ELSE 1 END,
                last_verified ASC,
                id ASC
            """
        ).fetchall()

    opportunity_ids = [
        row["id"]
        for row in rows
    ]

    if limit is not None:
        opportunity_ids = opportunity_ids[:limit]

    results = []

    for index, opportunity_id in enumerate(opportunity_ids):
        result = verify_opportunity(
            opportunity_id=opportunity_id,
            model=model,
            database_path=database_path,
            fetcher=fetcher,
            extractor=extractor
        )

        results.append(result)

        if (
            delay_seconds > 0
            and index < len(opportunity_ids) - 1
        ):
            time.sleep(delay_seconds)

    summary = {
        "total_checked": len(results),
        "verified": 0,
        "changed": 0,
        "inaccessible": 0,
        "not_found": 0,
        "failed": 0
    }

    for result in results:
        summary[result["outcome"]] += 1

    summary["results"] = results

    return summary
