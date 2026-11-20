
import pytest
from unittest.mock import patch

from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)

from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult,
    OpportunityExtractionResult
)


def create_opportunity_response(
    title: str,
    category: str = "Research"
) -> dict:
    """Create a valid opportunity extraction response."""
    return {
        "title": title,
        "organization": "Example University",
        "category": category,
        "opportunity_type": "Individual Position",
        "field": ["Computer Science"],
        "location": "Toronto, Canada",
        "work_mode": "In-person",
        "description": "A research position for undergraduate students.",
        "requirements": ["Enrolled undergraduate student"],
        "preferred_skills": ["Python"],
        "compensation": "Paid",
        "duration": "12 weeks",
        "start_date": None,
        "deadline": None,
        "eligibility": "Undergraduate students",
        "application_url": None,
        "evidence": [
            "Undergraduate Research Assistant position"
        ]
    }


def test_extract_page_with_llm():
    mock_response = """
    {
        "is_opportunity_page": true,
        "confidence": 0.95,
        "opportunities": [
            {
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
                "evidence": ["Undergraduate Research Assistant position"]
            }
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

    assert isinstance(result, PageExtractionResult)
    assert result.is_opportunity_page is True
    assert len(result.opportunities) == 1

    opportunity = result.opportunities[0]

    assert isinstance(opportunity, OpportunityExtractionResult)
    assert opportunity.title == "Undergraduate Research Assistant"
    assert opportunity.category.value == "Research"

    mock_generate.assert_called_once()


def test_extract_page_with_llm_accepts_multiple_opportunities():
    mock_response = {
        "is_opportunity_page": True,
        "confidence": 0.95,
        "opportunities": [
            create_opportunity_response(
                "Machine Learning Research Assistant"
            ),
            create_opportunity_response(
                "Biomedical Research Program"
            ),
            create_opportunity_response(
                "Environmental Research Internship"
            )
        ],
        "reasoning": "The page lists three distinct opportunities."
    }

    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value=__import__("json").dumps(mock_response)
    ):

        result = extract_page_with_llm("A directory of research opportunities.")

    assert result.is_opportunity_page is True
    assert len(result.opportunities) == 3

    titles = [opportunity.title for opportunity in result.opportunities]

    assert "Machine Learning Research Assistant" in titles
    assert "Biomedical Research Program" in titles
    assert "Environmental Research Internship" in titles


def test_extract_page_with_llm_accepts_no_opportunities():
    mock_response = """
    {
        "is_opportunity_page": false,
        "confidence": 0.95,
        "opportunities": [],
        "reasoning": "The page contains general career information."
    }
    """

    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value=mock_response
    ):

        result = extract_page_with_llm("General career information.")

    assert result.is_opportunity_page is False
    assert result.opportunities == []


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
    mock_response = {
        "is_opportunity_page": True,
        "confidence": 0.9,
        "opportunities": [
            create_opportunity_response(
                "Research Assistant",
                category="Something Invalid"
            )
        ],
        "reasoning": "The page describes a research position."
    }

    with patch(
        "opportunity_intelligence.extraction.llm_extractor.generate_response",
        return_value=__import__("json").dumps(mock_response)
    ):

        with pytest.raises(ValueError):
            extract_page_with_llm("Research assistant position.")
