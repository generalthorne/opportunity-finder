
from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    OpportunityType
)


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