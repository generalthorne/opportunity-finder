
import pytest

from pydantic import ValidationError

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult,
    PageExtractionResult
)

from opportunity_intelligence.models import (
    OpportunityCategory,
    OpportunityType
)


def test_extraction_result_accepts_valid_opportunity():
    result = OpportunityExtractionResult(
        title="Summer Research Internship",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.PROGRAM
    )

    assert result.title == "Summer Research Internship"
    assert result.organization == "Example University"
    assert result.category == OpportunityCategory.RESEARCH


def test_extraction_result_accepts_incomplete_information():
    result = OpportunityExtractionResult(
        title="Research Assistant Position"
    )

    assert result.title == "Research Assistant Position"
    assert result.organization is None
    assert result.category is None


def test_extraction_result_uses_empty_lists_by_default():
    result = OpportunityExtractionResult()

    assert result.field == []
    assert result.requirements == []
    assert result.preferred_skills == []
    assert result.evidence == []


def test_page_extraction_result_accepts_single_opportunity():
    opportunity = OpportunityExtractionResult(
        title="Summer Research Internship",
        organization="Example University",
        category=OpportunityCategory.RESEARCH
    )

    result = PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.95,
        opportunities=[opportunity]
    )

    assert result.is_opportunity_page is True
    assert len(result.opportunities) == 1
    assert result.opportunities[0].title == (
        "Summer Research Internship"
    )


def test_page_extraction_result_accepts_multiple_opportunities():
    opportunities = [
        OpportunityExtractionResult(
            title="Machine Learning Research Assistant"
        ),
        OpportunityExtractionResult(
            title="Biomedical Research Program"
        ),
        OpportunityExtractionResult(
            title="Environmental Research Internship"
        )
    ]

    result = PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.95,
        opportunities=opportunities
    )

    assert len(result.opportunities) == 3


def test_page_extraction_result_accepts_no_opportunities():
    result = PageExtractionResult(
        is_opportunity_page=False,
        confidence=0.95,
        reasoning="The page contains general career information."
    )

    assert result.is_opportunity_page is False
    assert result.opportunities == []


def test_page_extraction_result_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        PageExtractionResult(
            is_opportunity_page=True,
            confidence=1.5
        )


def test_page_extraction_result_uses_empty_list_by_default():
    result = PageExtractionResult(
        is_opportunity_page=False,
        confidence=0.9
    )

    assert result.opportunities == []
