
"""Tests for opportunity verification history."""

from datetime import datetime, timezone

import pytest

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    OpportunityType
)
from opportunity_intelligence.storage.repository import (
    get_all_opportunities,
    save_opportunities
)
from opportunity_intelligence.storage.verification import (
    get_verification_history,
    record_verification
)


def make_opportunity():
    return Opportunity(
        title="Machine Learning Research Assistant",
        organization="University of Toronto",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.INDIVIDUAL,
        description="Research position in machine learning.",
        source_url="https://example.com/research",
        status=OpportunityStatus.OPEN
    )


def create_stored_opportunity(database_path):
    result = save_opportunities(
        [make_opportunity()],
        database_path
    )

    assert result["inserted"] == 1

    return get_all_opportunities(database_path)[0]


def test_record_verification_creates_history(tmp_path):
    database_path = tmp_path / "test.db"
    opportunity = create_stored_opportunity(database_path)

    checked_at = datetime(
        2026, 11, 21, 15, 0, tzinfo=timezone.utc
    )

    history_id = record_verification(
        opportunity_id=1,
        outcome="verified",
        checked_at=checked_at,
        database_path=database_path
    )

    history = get_verification_history(
        1,
        database_path
    )

    assert history_id == 1
    assert len(history) == 1
    assert history[0]["outcome"] == "verified"
    assert history[0]["changed_fields"] == []
    assert history[0]["source_url"] == str(
        opportunity.source_url
    )


def test_verification_records_detected_changes(tmp_path):
    database_path = tmp_path / "test.db"
    create_stored_opportunity(database_path)

    record_verification(
        opportunity_id=1,
        outcome="changed",
        changed_fields=["deadline", "application_url"],
        previous_values={
            "deadline": "2027-02-01",
            "application_url": None
        },
        current_values={
            "deadline": "2027-03-01",
            "application_url": "https://example.com/apply"
        },
        database_path=database_path
    )

    history = get_verification_history(
        1,
        database_path
    )

    assert history[0]["changed_fields"] == [
        "deadline",
        "application_url"
    ]
    assert history[0]["previous_values"]["deadline"] == "2027-02-01"
    assert history[0]["current_values"]["deadline"] == "2027-03-01"


def test_verification_updates_last_verified(tmp_path):
    database_path = tmp_path / "test.db"
    create_stored_opportunity(database_path)

    checked_at = datetime(
        2026, 11, 21, 15, 0, tzinfo=timezone.utc
    )

    record_verification(
        opportunity_id=1,
        outcome="verified",
        checked_at=checked_at,
        database_path=database_path
    )

    stored = get_all_opportunities(database_path)[0]

    assert stored.last_verified == checked_at


def test_verification_can_update_status(tmp_path):
    database_path = tmp_path / "test.db"
    create_stored_opportunity(database_path)

    record_verification(
        opportunity_id=1,
        outcome="verified",
        status=OpportunityStatus.CLOSED,
        database_path=database_path
    )

    stored = get_all_opportunities(database_path)[0]

    assert stored.status == OpportunityStatus.CLOSED


def test_verification_history_is_newest_first(tmp_path):
    database_path = tmp_path / "test.db"
    create_stored_opportunity(database_path)

    first_check = datetime(
        2026, 11, 20, 12, 0, tzinfo=timezone.utc
    )
    second_check = datetime(
        2026, 11, 21, 12, 0, tzinfo=timezone.utc
    )

    record_verification(
        opportunity_id=1,
        outcome="verified",
        checked_at=first_check,
        database_path=database_path
    )

    record_verification(
        opportunity_id=1,
        outcome="changed",
        checked_at=second_check,
        database_path=database_path
    )

    history = get_verification_history(
        1,
        database_path
    )

    assert len(history) == 2
    assert history[0]["outcome"] == "changed"
    assert history[1]["outcome"] == "verified"


def test_invalid_verification_outcome_is_rejected(tmp_path):
    database_path = tmp_path / "test.db"
    create_stored_opportunity(database_path)

    with pytest.raises(ValueError):
        record_verification(
            opportunity_id=1,
            outcome="made_up_outcome",
            database_path=database_path
        )


def test_verification_rejects_unknown_opportunity(tmp_path):
    database_path = tmp_path / "test.db"

    with pytest.raises(ValueError):
        record_verification(
            opportunity_id=999,
            outcome="verified",
            database_path=database_path
        )
