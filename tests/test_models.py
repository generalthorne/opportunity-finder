
from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    OpportunityType
)

import pytest
from pydantic import ValidationError

from opportunity_intelligence.models import Opportunity


def test_create_opportunity():
    opportunity = Opportunity(
        title="ML Research Assistant",
        organization="University of Toronto",
        category=OpportunityCategory.RESEARCH,
        field=["Machine Learning", "Computer Science"],
        location="Toronto, Canada",
        source_url="https://example.com/research",
        status=OpportunityStatus.OPEN
    )

    assert opportunity.title == "ML Research Assistant"
    assert opportunity.organization == "University of Toronto"
    assert opportunity.category == OpportunityCategory.RESEARCH
    assert opportunity.status == OpportunityStatus.OPEN
    assert opportunity.compensation is None


def test_opportunity_type():
    opportunity = Opportunity(
        title="PEY Co-op",
        organization="University of Toronto",
        category=OpportunityCategory.COOP,
        opportunity_type=OpportunityType.PROGRAM,
        source_url="https://example.com"
    )

    assert opportunity.opportunity_type == OpportunityType.PROGRAM


def test_opportunity_trims_required_text():
    opportunity = Opportunity(
        title="  Research Assistant  ",
        organization="  University of Toronto  ",
        category="Research",
        source_url="https://example.com"
    )

    assert opportunity.title == "Research Assistant"
    assert opportunity.organization == "University of Toronto"


@pytest.mark.parametrize(
    "field",
    ["title", "organization"]
)
def test_opportunity_rejects_empty_required_text(field):
    data = {
        "title": "Research Assistant",
        "organization": "University of Toronto",
        "category": "Research",
        "source_url": "https://example.com"
    }

    data[field] = "   "

    with pytest.raises(ValidationError):
        Opportunity.model_validate(data)

def test_opportunity_preserves_evidence():
    opportunity = Opportunity(
        title="Research Assistant",
        organization="University of Toronto",
        category="Research",
        source_url="https://example.com",
        evidence=[
            "Applications are open to undergraduate students.",
            "The position runs from May to August."
        ]
    )

    assert len(opportunity.evidence) == 2
    assert "Applications are open to undergraduate students." in opportunity.evidence


def test_opportunity_evidence_defaults_to_empty_list():
    opportunity = Opportunity(
        title="Research Assistant",
        organization="University of Toronto",
        category="Research",
        source_url="https://example.com"
    )

    assert opportunity.evidence == []