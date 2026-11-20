import pytest

from pydantic import ValidationError

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult
)

from opportunity_intelligence.models import (
    OpportunityCategory,
    OpportunityType
)


def test_extraction_result_accepts_valid_opportunity():
    result = OpportunityExtractionResult(
        is_opportunity=True,
        confidence=0.95,
        title="Summer Research Internship",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.PROGRAM
    )

    assert result.is_opportunity is True
    assert result.title == "Summer Research Internship"


def test_extraction_result_accepts_incomplete_information():
    result = OpportunityExtractionResult(
        is_opportunity=True,
        confidence=0.7,
        title="Research Assistant Position"
    )

    assert result.title == "Research Assistant Position"
    assert result.organization is None
    assert result.category is None


def test_extraction_result_accepts_non_opportunity():
    result = OpportunityExtractionResult(
        is_opportunity=False,
        confidence=0.95,
        reasoning="The page only provides general career information."
    )

    assert result.is_opportunity is False


def test_extraction_result_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        OpportunityExtractionResult(
            is_opportunity=True,
            confidence=1.5
        )


def test_extraction_result_uses_empty_lists_by_default():
    result = OpportunityExtractionResult(
        is_opportunity=True,
        confidence=0.8
    )

    assert result.field == []
    assert result.requirements == []
    assert result.preferred_skills == []
    assert result.evidence == []