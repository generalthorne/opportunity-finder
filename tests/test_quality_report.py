
from opportunity_intelligence.models import Opportunity

from opportunity_intelligence.extraction.quality_report import (
    build_quality_report,
    is_missing
)


def create_opportunity(**overrides):
    data = {
        "title": "Research Assistant",
        "organization": "Example University",
        "category": "Research",
        "source_url": "https://example.com",
        "description": "A summer research position.",
        "location": "Toronto",
        "eligibility": "Undergraduate students",
        "requirements": ["Enrolled in university"],
        "deadline": "2027-02-01",
        "application_url": "https://example.com/apply",
        "evidence": ["Applications are open."]
    }

    data.update(overrides)

    return Opportunity(**data)


def test_is_missing():
    assert is_missing(None)
    assert is_missing("")
    assert is_missing("   ")
    assert is_missing([])
    assert not is_missing("Research")
    assert not is_missing(["Python"])


def test_quality_report_complete_opportunity():
    opportunity = create_opportunity()

    report = build_quality_report([opportunity])

    assert report["total_opportunities"] == 1
    assert report["opportunities_needing_review"] == 0
    assert report["records_needing_review"] == []


def test_quality_report_identifies_missing_fields():
    opportunity = create_opportunity(
        description=None,
        deadline=None,
        evidence=[]
    )

    report = build_quality_report([opportunity])

    assert report["total_opportunities"] == 1
    assert report["opportunities_needing_review"] == 1

    assert report["missing_field_counts"]["description"] == 1
    assert report["missing_field_counts"]["deadline"] == 1
    assert report["missing_field_counts"]["evidence"] == 1

    missing_fields = (
        report["records_needing_review"][0]["missing_fields"]
    )

    assert "description" in missing_fields
    assert "deadline" in missing_fields
    assert "evidence" in missing_fields


def test_quality_report_handles_empty_dataset():
    report = build_quality_report([])

    assert report["total_opportunities"] == 0
    assert report["opportunities_needing_review"] == 0
    assert report["records_needing_review"] == []
