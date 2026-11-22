
"""Database operations for opportunity records."""

import json
import sqlite3

from opportunity_intelligence.models import Opportunity
from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    get_connection,
    initialize_database
)

from difflib import SequenceMatcher
import re


LIST_FIELDS = {
    "field",
    "evidence",
    "requirements",
    "preferred_skills",
    "related_source_urls"
}


def serialize_opportunity(
    opportunity: Opportunity
) -> dict:
    """Convert an Opportunity into database-compatible values."""

    data = opportunity.model_dump(mode="json")

    for field in LIST_FIELDS:
        data[field] = json.dumps(
            data[field],
            ensure_ascii=False
        )

    return data


def deserialize_opportunity(
    row: sqlite3.Row
) -> Opportunity:
    """Convert a database row back into an Opportunity."""

    data = dict(row)

    for field in LIST_FIELDS:
        value = data.get(field)

        if value:
            data[field] = json.loads(value)
        else:
            data[field] = []

    data.pop("id", None)
    data.pop("created_at", None)
    data.pop("updated_at", None)

    return Opportunity.model_validate(data)


def normalize_title(title: str) -> str:
    """Normalize a title for duplicate comparison."""

    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def find_existing_opportunity(
    connection: sqlite3.Connection,
    opportunity: Opportunity
) -> sqlite3.Row | None:
    """Find an existing record despite minor title or metadata differences."""

    incoming_title = normalize_title(opportunity.title)

    # First, look for an exact title match regardless of organization
    # or category.
    exact_match = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE lower(trim(title)) = lower(trim(?))
        LIMIT 1
        """,
        (opportunity.title,)
    ).fetchone()

    if exact_match:
        return exact_match

    # Then compare titles from the same source page. This handles
    # small title variations without merging unrelated opportunities.
    candidates = connection.execute(
        """
        SELECT *
        FROM opportunities
        WHERE source_url = ?
        """,
        (str(opportunity.source_url),)
    ).fetchall()

    for candidate in candidates:
        existing_title = normalize_title(candidate["title"])

        if (
            existing_title in incoming_title
            or incoming_title in existing_title
            or SequenceMatcher(
                None,
                existing_title,
                incoming_title
            ).ratio() >= 0.85
        ):
            return candidate

    return None


def merge_source_urls(
    existing: sqlite3.Row,
    incoming: Opportunity
) -> list[str]:
    """Merge source URLs without introducing duplicates."""

    urls = [
        existing["source_url"],
        *json.loads(existing["related_source_urls"] or "[]"),
        str(incoming.source_url),
        *(str(url) for url in incoming.related_source_urls)
    ]

    unique_urls = []
    seen = set()

    for url in urls:
        if url and url not in seen:
            unique_urls.append(url)
            seen.add(url)

    return unique_urls



def merge_opportunity_data(
    existing: sqlite3.Row,
    incoming: dict
) -> dict:
    """Merge incoming data while preserving useful existing information."""

    merged = dict(incoming)

    # Combine list fields without duplicates.
    for field in LIST_FIELDS:
        existing_value = json.loads(existing[field] or "[]")
        incoming_value = json.loads(incoming[field] or "[]")

        combined = []
        seen = set()

        for value in [*existing_value, *incoming_value]:
            if value not in seen:
                combined.append(value)
                seen.add(value)

        merged[field] = json.dumps(
            combined,
            ensure_ascii=False
        )

    # Preserve existing values when the incoming extraction is empty.
    for field, incoming_value in incoming.items():
        if field in LIST_FIELDS:
            continue

        existing_value = existing[field]

        if incoming_value is None or incoming_value == "":
            merged[field] = existing_value

    # Preserve a known status if the new extraction cannot determine it.
    if (
        incoming["status"] == "Unknown"
        and existing["status"] not in (None, "", "Unknown")
    ):
        merged["status"] = existing["status"]

    # Preserve the original primary source and discovery date.
    merged["source_url"] = existing["source_url"]
    merged["date_discovered"] = (
        existing["date_discovered"]
        or incoming["date_discovered"]
    )

    # Preserve the verification timestamp unless a newer one is supplied.
    if incoming["last_verified"] is None:
        merged["last_verified"] = existing["last_verified"]

    # Combine source URLs.
    related_urls = json.loads(
        existing["related_source_urls"] or "[]"
    )

    incoming_source = incoming["source_url"]

    if (
        incoming_source
        and incoming_source != existing["source_url"]
        and incoming_source not in related_urls
    ):
        related_urls.append(incoming_source)

    merged["related_source_urls"] = json.dumps(
        related_urls,
        ensure_ascii=False
    )

    return merged



def save_opportunities(
    opportunities: list[Opportunity],
    database_path=DEFAULT_DATABASE
) -> dict:
    """Insert new opportunities and safely update existing records."""

    initialize_database(database_path)

    inserted = 0
    updated = 0

    with get_connection(database_path) as connection:
        for opportunity in opportunities:
            existing = find_existing_opportunity(
                connection,
                opportunity
            )

            data = serialize_opportunity(opportunity)

            if existing is None:
                connection.execute(
                    """
                    INSERT INTO opportunities (
                        title,
                        organization,
                        category,
                        opportunity_type,
                        field,
                        location,
                        work_mode,
                        description,
                        evidence,
                        requirements,
                        preferred_skills,
                        compensation,
                        duration,
                        start_date,
                        deadline,
                        start_date_text,
                        deadline_text,
                        eligibility,
                        application_url,
                        source_url,
                        related_source_urls,
                        date_discovered,
                        last_verified,
                        status
                    )
                    VALUES (
                        :title,
                        :organization,
                        :category,
                        :opportunity_type,
                        :field,
                        :location,
                        :work_mode,
                        :description,
                        :evidence,
                        :requirements,
                        :preferred_skills,
                        :compensation,
                        :duration,
                        :start_date,
                        :deadline,
                        :start_date_text,
                        :deadline_text,
                        :eligibility,
                        :application_url,
                        :source_url,
                        :related_source_urls,
                        :date_discovered,
                        :last_verified,
                        :status
                    )
                    """,
                    data
                )

                inserted += 1

            else:
                data = merge_opportunity_data(
                    existing,
                    data
                )

                connection.execute(
                    """
                    UPDATE opportunities
                    SET
                        opportunity_type = :opportunity_type,
                        category = :category,
                        field = :field,
                        location = :location,
                        work_mode = :work_mode,
                        description = :description,
                        evidence = :evidence,
                        requirements = :requirements,
                        preferred_skills = :preferred_skills,
                        compensation = :compensation,
                        duration = :duration,
                        start_date = :start_date,
                        deadline = :deadline,
                        start_date_text = :start_date_text,
                        deadline_text = :deadline_text,
                        eligibility = :eligibility,
                        application_url = :application_url,
                        related_source_urls = :related_source_urls,
                        date_discovered = :date_discovered,
                        last_verified = :last_verified,
                        status = :status,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                    """,
                    {
                        **data,
                        "id": existing["id"]
                    }
                )

                updated += 1

    return {
        "inserted": inserted,
        "updated": updated,
        "total_processed": inserted + updated
    }



def get_all_opportunities(
    database_path=DEFAULT_DATABASE
) -> list[Opportunity]:
    """Retrieve all stored opportunities."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM opportunities
            ORDER BY title COLLATE NOCASE
            """
        ).fetchall()

    return [
        deserialize_opportunity(row)
        for row in rows
    ]


def get_opportunity_by_id(
    opportunity_id: int,
    database_path=DEFAULT_DATABASE
) -> Opportunity | None:
    """Retrieve one opportunity by its database ID."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        row = connection.execute(
            """
            SELECT *
            FROM opportunities
            WHERE id = ?
            """,
            (opportunity_id,)
        ).fetchone()

    if row is None:
        return None

    return deserialize_opportunity(row)


def search_opportunities(
    search_term: str,
    database_path=DEFAULT_DATABASE
) -> list[Opportunity]:
    """Search opportunity titles, organizations, and descriptions."""

    initialize_database(database_path)

    pattern = f"%{search_term.strip()}%"

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM opportunities
            WHERE title LIKE ?
            OR organization LIKE ?
            OR description LIKE ?
            ORDER BY title COLLATE NOCASE
            """,
            (pattern, pattern, pattern)
        ).fetchall()

    return [
        deserialize_opportunity(row)
        for row in rows
    ]


def get_opportunities_by_category(
    category: str,
    database_path=DEFAULT_DATABASE
) -> list[Opportunity]:
    """Retrieve opportunities belonging to a category."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM opportunities
            WHERE category = ?
            ORDER BY title COLLATE NOCASE
            """,
            (category,)
        ).fetchall()

    return [
        deserialize_opportunity(row)
        for row in rows
    ]


def delete_opportunity(
    opportunity_id: int,
    database_path=DEFAULT_DATABASE
) -> bool:
    """Delete an opportunity and report whether it existed."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        cursor = connection.execute(
            """
            DELETE FROM opportunities
            WHERE id = ?
            """,
            (opportunity_id,)
        )

    return cursor.rowcount > 0


def count_opportunities(
    database_path=DEFAULT_DATABASE
) -> int:
    """Return the number of stored opportunities."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM opportunities"
        ).fetchone()

    return result[0]
