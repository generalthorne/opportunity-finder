
import pytest
from unittest.mock import patch

from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult
)


def test_extract_page_with_llm():
    mock_response = """
    {
        "is_opportunity": true,
        "confidence": 0.95,
        "title": "Undergraduate Research Assistant",
        "organization": "Example University",
        "category": "Research",
        "opportunity_type": "Individual Position",
        "field": ["Computer Science"],
        "location": "Toronto, Canada",
        "work_mode": "In-person",
        "description": "A research position for undergraduate students.",
        "requirements": ["Enrolled undergraduate student"],
        "preferred_skills": ["Python"],
        "compensation": "Paid",
        "duration": "12 weeks",
        "start_date": null,
        "deadline": null,
        "eligibility": "Undergraduate students",
        "application_url": null,
        "evidence": [
            "Undergraduate Research Assistant position"
        ],
        "reasoning": "The page describes a specific research position."
    }
    """

    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value=mock_response
    ) as mock_generate:

        result = extract_page_with_llm(
            page_text="An undergraduate research assistant position.",
            page_title="Research Assistant"
        )

    assert isinstance(result, OpportunityExtractionResult)
    assert result.is_opportunity is True
    assert result.title == "Undergraduate Research Assistant"
    assert result.category.value == "Research"

    mock_generate.assert_called_once()


def test_extract_page_with_llm_rejects_empty_text():
    with pytest.raises(ValueError):
        extract_page_with_llm("")


def test_extract_page_with_llm_rejects_invalid_json():
    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value="This is not valid JSON."
    ):

        with pytest.raises(ValueError):
            extract_page_with_llm("Some webpage content.")


def test_extract_page_with_llm_rejects_invalid_category():
    mock_response = """
    {
        "is_opportunity": true,
        "confidence": 0.9,
        "title": "Research Assistant",
        "organization": "Example University",
        "category": "Something Invalid",
        "opportunity_type": "Individual Position"
    }
    """

    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value=mock_response
    ):

        with pytest.raises(ValueError):
            extract_page_with_llm("Research assistant position.")
