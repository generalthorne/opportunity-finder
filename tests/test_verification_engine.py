
"""Tests for the opportunity verification engine."""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from bs4 import BeautifulSoup

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory
)
from opportunity_intelligence.storage.database import (
    initialize_database
)
from opportunity_intelligence.storage.repository import (
    save_opportunities,
    get_opportunity_by_id
)
from opportunity_intelligence.storage.verification import (
    get_verification_history
)
from opportunity_intelligence.verification.verification_engine import (
    verify_opportunity,
    verify_all_opportunities
)


@pytest.fixture
def stored_opportunity(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    opportunity = Opportunity(
        title="Undergraduate Research Assistant",
        organization="University of Toronto",
        category=OpportunityCategory.RESEARCH,
        description="Research position in computer science.",
        location="Toronto, Canada",
        eligibility="Undergraduate students",
        source_url="https://example.com/research"
    )

    save_opportunities(
        [opportunity],
        database_path
    )

    return database_path, opportunity


def successful_fetch():
    return SimpleNamespace(
        soup=BeautifulSoup(
            """
            <html>
                <head><title>Research Opportunity</title></head>
                <body>
                    Undergraduate Research Assistant
                    University of Toronto
                </body>
            </html>
            """,
            "html.parser"
        ),
        status_code=200,
        error=None
    )


def make_extractor(opportunities):
    def extractor(page, model=None):
        return opportunities

    return extractor


def test_verify_opportunity_without_changes(stored_opportunity):
    database_path, opportunity = stored_opportunity

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([opportunity])
    )

    assert result["outcome"] == "verified"
    assert result["changed_fields"] == []

    history = get_verification_history(
        1,
        database_path
    )

    assert len(history) == 1
    assert history[0]["outcome"] == "verified"

    updated = get_opportunity_by_id(
        1,
        database_path
    )

    assert updated.last_verified is not None


def test_verify_opportunity_detects_changes(stored_opportunity):
    database_path, opportunity = stored_opportunity

    extracted = opportunity.model_copy(
        update={
            "description": "Updated research position description."
        }
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([extracted])
    )

    assert result["outcome"] == "changed"
    assert "description" in result["changed_fields"]

    updated = get_opportunity_by_id(
        1,
        database_path
    )

    assert updated.description == (
        "Updated research position description."
    )


def test_verify_does_not_overwrite_existing_data_with_empty_values(
    stored_opportunity
):
    database_path, opportunity = stored_opportunity

    extracted = opportunity.model_copy(
        update={
            "description": None,
            "location": None
        }
    )

    verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([extracted])
    )

    updated = get_opportunity_by_id(
        1,
        database_path
    )

    assert updated.description == opportunity.description
    assert updated.location == opportunity.location


def test_verify_records_not_found(stored_opportunity):
    database_path, _ = stored_opportunity

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([])
    )

    assert result["outcome"] == "not_found"

    history = get_verification_history(
        1,
        database_path
    )

    assert history[0]["outcome"] == "not_found"

    updated = get_opportunity_by_id(
        1,
        database_path
    )

    assert updated.last_verified is None


def test_verify_records_inaccessible_page(stored_opportunity):
    database_path, _ = stored_opportunity

    failed_fetch = SimpleNamespace(
        soup=None,
        status_code=403,
        error="403 Forbidden"
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: failed_fetch
    )

    assert result["outcome"] == "inaccessible"

    history = get_verification_history(
        1,
        database_path
    )

    assert history[0]["outcome"] == "inaccessible"

    updated = get_opportunity_by_id(
        1,
        database_path
    )

    assert updated.last_verified is None


def test_verify_records_missing_page(stored_opportunity):
    database_path, _ = stored_opportunity

    missing_fetch = SimpleNamespace(
        soup=None,
        status_code=404,
        error="404 Not Found"
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: missing_fetch
    )

    assert result["outcome"] == "not_found"


def test_verify_records_extraction_failure(stored_opportunity):
    database_path, _ = stored_opportunity

    def failing_extractor(page, model=None):
        raise RuntimeError("Mock extraction failure")

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=failing_extractor
    )

    assert result["outcome"] == "failed"

    history = get_verification_history(
        1,
        database_path
    )

    assert history[0]["outcome"] == "failed"


def test_verify_rejects_nonexistent_opportunity(tmp_path):
    database_path = tmp_path / "test.db"

    initialize_database(database_path)

    with pytest.raises(ValueError):
        verify_opportunity(
            opportunity_id=999,
            database_path=database_path
        )


def test_verify_all_opportunities(stored_opportunity):
    database_path, opportunity = stored_opportunity

    second_opportunity = Opportunity(
        title="Software Engineering Intern",
        organization="Example Company",
        category=OpportunityCategory.INTERNSHIP,
        source_url="https://example.com/internship"
    )

    save_opportunities(
        [second_opportunity],
        database_path
    )

    summary = verify_all_opportunities(
        database_path=database_path,
        delay_seconds=0,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([opportunity])
    )

    assert summary["total_checked"] == 2
    assert summary["verified"] == 1
    assert summary["not_found"] == 1
    assert len(summary["results"]) == 2


def test_verify_all_respects_limit(stored_opportunity):
    database_path, opportunity = stored_opportunity

    second_opportunity = Opportunity(
        title="Software Engineering Intern",
        organization="Example Company",
        category=OpportunityCategory.INTERNSHIP,
        source_url="https://example.com/internship"
    )

    save_opportunities(
        [second_opportunity],
        database_path
    )

    summary = verify_all_opportunities(
        limit=1,
        database_path=database_path,
        delay_seconds=0,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([opportunity])
    )

    assert summary["total_checked"] == 1


def test_verify_all_rejects_invalid_limit(stored_opportunity):
    database_path, _ = stored_opportunity

    with pytest.raises(ValueError):
        verify_all_opportunities(
            limit=0,
            database_path=database_path
        )



def test_verify_rejects_different_organization(stored_opportunity):
    database_path, opportunity = stored_opportunity

    unrelated = opportunity.model_copy(
        update={
            "organization": "Different University"
        }
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([unrelated])
    )

    assert result["outcome"] == "not_found"


def test_verify_rejects_different_category(stored_opportunity):
    database_path, opportunity = stored_opportunity

    unrelated = opportunity.model_copy(
        update={
            "category": OpportunityCategory.INTERNSHIP
        }
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([unrelated])
    )

    assert result["outcome"] == "not_found"


def test_verify_ignores_list_order_changes(stored_opportunity):
    database_path, opportunity = stored_opportunity

    original = opportunity.model_copy(
        update={
            "field": ["Computer Science", "Machine Learning"]
        }
    )

    save_opportunities([original], database_path)

    reordered = original.model_copy(
        update={
            "field": ["Machine Learning", "Computer Science"]
        }
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: successful_fetch(),
        extractor=make_extractor([reordered])
    )

    assert result["outcome"] == "verified"
    assert "field" not in result["changed_fields"]


def test_verify_records_empty_page_as_failed(stored_opportunity):
    database_path, _ = stored_opportunity

    empty_fetch = SimpleNamespace(
        soup=BeautifulSoup(
            "<html><body></body></html>",
            "html.parser"
        ),
        status_code=200,
        error=None
    )

    result = verify_opportunity(
        opportunity_id=1,
        database_path=database_path,
        fetcher=lambda url: empty_fetch
    )

    assert result["outcome"] == "failed"
