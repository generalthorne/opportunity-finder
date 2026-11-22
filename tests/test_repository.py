
from datetime import date

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    OpportunityType
)

from opportunity_intelligence.storage.repository import (
    count_opportunities,
    delete_opportunity,
    get_all_opportunities,
    get_opportunity_by_id,
    get_opportunities_by_category,
    save_opportunities,
    search_opportunities
)


def make_opportunity(
    title="Machine Learning Research Assistant",
    organization="University of Toronto",
    source_url="https://example.com/research",
    **overrides
):
    data = {
        "title": title,
        "organization": organization,
        "category": OpportunityCategory.RESEARCH,
        "opportunity_type": OpportunityType.INDIVIDUAL,
        "field": ["Computer Science", "Machine Learning"],
        "location": "Toronto, Canada",
        "description": "Research involving machine learning.",
        "evidence": ["Research position described on source page."],
        "requirements": ["Undergraduate student"],
        "preferred_skills": ["Python"],
        "deadline": date(2027, 3, 1),
        "eligibility": "Undergraduate students",
        "source_url": source_url,
        "status": OpportunityStatus.OPEN
    }

    data.update(overrides)

    return Opportunity(**data)


def test_save_opportunities_inserts_records(tmp_path):
    database_path = tmp_path / "test.db"

    opportunity = make_opportunity()

    result = save_opportunities(
        [opportunity],
        database_path
    )

    assert result["inserted"] == 1
    assert result["updated"] == 0
    assert count_opportunities(database_path) == 1


def test_get_all_opportunities_restores_full_records(tmp_path):
    database_path = tmp_path / "test.db"

    opportunity = make_opportunity()

    save_opportunities([opportunity], database_path)

    records = get_all_opportunities(database_path)

    assert len(records) == 1
    assert records[0].title == opportunity.title
    assert records[0].field == opportunity.field
    assert records[0].requirements == opportunity.requirements
    assert records[0].deadline == opportunity.deadline
    assert records[0].status == opportunity.status
    assert records[0].source_url == opportunity.source_url


def test_duplicate_opportunity_updates_existing_record(tmp_path):
    database_path = tmp_path / "test.db"

    original = make_opportunity()

    updated = make_opportunity(
        description="Updated research description."
    )

    save_opportunities([original], database_path)

    result = save_opportunities(
        [updated],
        database_path
    )

    records = get_all_opportunities(database_path)

    assert result["inserted"] == 0
    assert result["updated"] == 1
    assert count_opportunities(database_path) == 1
    assert records[0].description == "Updated research description."


def test_duplicate_opportunity_merges_source_urls(tmp_path):
    database_path = tmp_path / "test.db"

    original = make_opportunity(
        source_url="https://example.com/research"
    )

    duplicate = make_opportunity(
        source_url="https://example.com/alternate"
    )

    save_opportunities([original], database_path)
    save_opportunities([duplicate], database_path)

    records = get_all_opportunities(database_path)

    assert len(records) == 1
    assert str(records[0].source_url) == "https://example.com/research"
    assert "https://example.com/alternate" in [
        str(url) for url in records[0].related_source_urls
    ]


def test_get_opportunity_by_id(tmp_path):
    database_path = tmp_path / "test.db"

    save_opportunities(
        [make_opportunity()],
        database_path
    )

    from opportunity_intelligence.storage.database import (
        get_connection
    )

    with get_connection(database_path) as connection:
        result = connection.execute(
            "SELECT id FROM opportunities"
        ).fetchone()

    opportunity = get_opportunity_by_id(
        result["id"],
        database_path
    )

    assert opportunity is not None
    assert opportunity.title == "Machine Learning Research Assistant"


def test_search_opportunities(tmp_path):
    database_path = tmp_path / "test.db"

    save_opportunities(
        [
            make_opportunity(),
            make_opportunity(
                title="Software Engineering Intern",
                organization="Example Company",
                source_url="https://example.com/internship",
                category=OpportunityCategory.INTERNSHIP,
                description="Software engineering internship."
            )
        ],
        database_path
    )

    results = search_opportunities(
        "Machine Learning",
        database_path
    )

    assert len(results) == 1
    assert results[0].title == "Machine Learning Research Assistant"


def test_get_opportunities_by_category(tmp_path):
    database_path = tmp_path / "test.db"

    save_opportunities(
        [
            make_opportunity(),
            make_opportunity(
                title="Software Engineering Intern",
                organization="Example Company",
                source_url="https://example.com/internship",
                category=OpportunityCategory.INTERNSHIP
            )
        ],
        database_path
    )

    results = get_opportunities_by_category(
        "Research",
        database_path
    )

    assert len(results) == 1
    assert results[0].category == OpportunityCategory.RESEARCH


def test_delete_opportunity(tmp_path):
    database_path = tmp_path / "test.db"

    save_opportunities(
        [make_opportunity()],
        database_path
    )

    from opportunity_intelligence.storage.database import (
        get_connection
    )

    with get_connection(database_path) as connection:
        result = connection.execute(
            "SELECT id FROM opportunities"
        ).fetchone()

    assert delete_opportunity(result["id"], database_path)
    assert count_opportunities(database_path) == 0


def test_delete_nonexistent_opportunity_returns_false(tmp_path):
    database_path = tmp_path / "test.db"

    assert not delete_opportunity(999, database_path)


def test_saving_empty_list_does_not_change_database(tmp_path):
    database_path = tmp_path / "test.db"

    save_opportunities(
        [make_opportunity()],
        database_path
    )

    result = save_opportunities([], database_path)

    assert result["inserted"] == 0
    assert result["updated"] == 0
    assert count_opportunities(database_path) == 1
