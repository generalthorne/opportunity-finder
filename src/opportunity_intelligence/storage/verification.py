
"""Record and retrieve opportunity verification history."""

import json
from datetime import datetime, timezone

from opportunity_intelligence.models import OpportunityStatus
from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    get_connection,
    initialize_database
)


VALID_OUTCOMES = {
    "verified",
    "changed",
    "inaccessible",
    "failed",
    "not_found"
}

SUCCESSFUL_OUTCOMES = {
    "verified",
    "changed"
}


def record_verification(
    opportunity_id: int,
    outcome: str,
    changed_fields: list[str] | None = None,
    previous_values: dict | None = None,
    current_values: dict | None = None,
    source_url: str | None = None,
    notes: str | None = None,
    status: OpportunityStatus | str | None = None,
    checked_at: datetime | None = None,
    database_path=DEFAULT_DATABASE
) -> int:
    """Record a verification event and update verification metadata."""

    if outcome not in VALID_OUTCOMES:
        raise ValueError(
            f"Invalid verification outcome: {outcome}"
        )

    if status is not None:
        status = (
            status.value
            if isinstance(status, OpportunityStatus)
            else status
        )

        valid_statuses = {
            item.value for item in OpportunityStatus
        }

        if status not in valid_statuses:
            raise ValueError(
                f"Invalid opportunity status: {status}"
            )

    if checked_at is None:
        checked_at = datetime.now(timezone.utc)

    checked_at_text = checked_at.isoformat()

    changed_fields = changed_fields or []
    previous_values = previous_values or {}
    current_values = current_values or {}

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        opportunity = connection.execute(
            """
            SELECT id, source_url
            FROM opportunities
            WHERE id = ?
            """,
            (opportunity_id,)
        ).fetchone()

        if opportunity is None:
            raise ValueError(
                f"Opportunity {opportunity_id} does not exist."
            )

        cursor = connection.execute(
            """
            INSERT INTO verification_history (
                opportunity_id,
                checked_at,
                outcome,
                changed_fields,
                previous_values,
                current_values,
                source_url,
                notes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                opportunity_id,
                checked_at_text,
                outcome,
                json.dumps(changed_fields, ensure_ascii=False),
                json.dumps(previous_values, ensure_ascii=False),
                json.dumps(current_values, ensure_ascii=False),
                source_url or opportunity["source_url"],
                notes
            )
        )

        if outcome in SUCCESSFUL_OUTCOMES:
            if status is None:
                connection.execute(
                    """
                    UPDATE opportunities
                    SET last_verified = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (checked_at_text, opportunity_id)
                )
            else:
                connection.execute(
                    """
                    UPDATE opportunities
                    SET last_verified = ?,
                        status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (checked_at_text, status, opportunity_id)
                )
        else:
            connection.execute(
                """
                UPDATE opportunities
                SET updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (opportunity_id,)
            )

        return cursor.lastrowid


def get_verification_history(
    opportunity_id: int,
    database_path=DEFAULT_DATABASE
) -> list[dict]:
    """Retrieve verification events for one opportunity, newest first."""

    initialize_database(database_path)

    with get_connection(database_path) as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM verification_history
            WHERE opportunity_id = ?
            ORDER BY checked_at DESC, id DESC
            """,
            (opportunity_id,)
        ).fetchall()

    history = []

    for row in rows:
        record = dict(row)

        record["changed_fields"] = json.loads(
            record["changed_fields"]
        )
        record["previous_values"] = json.loads(
            record["previous_values"]
        )
        record["current_values"] = json.loads(
            record["current_values"]
        )

        history.append(record)

    return history
