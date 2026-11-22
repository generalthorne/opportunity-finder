
from unittest.mock import patch

from opportunity_intelligence.extraction.page_extractor import (
    extract_opportunities_from_page,
    convert_extraction_to_opportunities,
    parse_date,
    should_send_page_to_llm,
)

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult,
    PageExtractionResult
)

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityType
)


def create_page(
    status="success",
    page_text=(
        "Undergraduate Research Assistant positions are available. "
        "Students can apply to work with faculty on research projects. "
        * 10
    ),
    url="https://example.com/research"
):
    """Create a representative investigated opportunity page."""
    return {
        "status": status,
        "url": url,
        "page_title": "Research Opportunities",
        "page_text": page_text
    }


def create_extraction_result():
    """Create a representative LLM extraction result."""
    opportunity = OpportunityExtractionResult(
        title="Undergraduate Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.INDIVIDUAL,
        field=["Computer Science"],
        location="Toronto, Canada",
        description="A research position for undergraduate students.",
        requirements=["Currently enrolled undergraduate student"],
        compensation="Paid",
        duration="12 weeks",
        deadline="March 15, 2027",
        evidence=["Undergraduate Research Assistant position"]
    )

    return PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.95,
        opportunities=[opportunity]
    )


def test_extract_opportunities_from_page():
    page = create_page()
    extraction_result = create_extraction_result()

    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm",
        return_value=extraction_result
    ) as mock_extract:

        results = extract_opportunities_from_page(page)

    assert len(results) == 1
    assert isinstance(results[0], Opportunity)
    assert results[0].title == "Undergraduate Research Assistant"
    assert results[0].organization == "Example University"
    assert results[0].category == OpportunityCategory.RESEARCH
    assert str(results[0].source_url) == page["url"]

    mock_extract.assert_called_once()


def test_extract_opportunities_from_page_handles_multiple_opportunities():
    first = create_extraction_result().opportunities[0]

    second = OpportunityExtractionResult(
        title="Biomedical Research Program",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.PROGRAM,
        field=["Biology"],
        evidence=["Biomedical Research Program"]
    )

    extraction_result = PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.95,
        opportunities=[first, second]
    )

    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm",
        return_value=extraction_result
    ):

        results = extract_opportunities_from_page(create_page())

    assert len(results) == 2
    assert results[0].title == "Undergraduate Research Assistant"
    assert results[1].title == "Biomedical Research Program"


def test_extract_opportunities_from_page_handles_non_opportunity_page():
    extraction_result = PageExtractionResult(
        is_opportunity_page=False,
        confidence=0.95,
        opportunities=[]
    )

    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm",
        return_value=extraction_result
    ):

        results = extract_opportunities_from_page(create_page())

    assert results == []


def test_extract_opportunities_from_page_skips_failed_page():
    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
    ) as mock_extract:

        results = extract_opportunities_from_page(
            create_page(status="failed")
        )

    assert results == []
    mock_extract.assert_not_called()


def test_extract_opportunities_from_page_skips_empty_text():
    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
    ) as mock_extract:

        results = extract_opportunities_from_page(
            create_page(page_text="")
        )

    assert results == []
    mock_extract.assert_not_called()


def test_extract_opportunities_from_page_skips_missing_url():
    page = create_page()
    page["url"] = None

    with patch(
        "opportunity_intelligence.extraction.page_extractor.extract_page_with_llm"
    ) as mock_extract:

        results = extract_opportunities_from_page(page)

    assert results == []
    mock_extract.assert_not_called()


def test_convert_extraction_skips_missing_title():
    opportunity = OpportunityExtractionResult(
        organization="Example University",
        category=OpportunityCategory.RESEARCH
    )

    extraction_result = PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.9,
        opportunities=[opportunity]
    )

    results = convert_extraction_to_opportunities(
        extraction_result,
        "https://example.com/research"
    )

    assert results == []


def test_convert_extraction_skips_missing_organization():
    opportunity = OpportunityExtractionResult(
        title="Research Assistant",
        category=OpportunityCategory.RESEARCH
    )

    extraction_result = PageExtractionResult(
        is_opportunity_page=True,
        confidence=0.9,
        opportunities=[opportunity]
    )

    results = convert_extraction_to_opportunities(
        extraction_result,
        "https://example.com/research"
    )

    assert results == []


def test_parse_date_accepts_supported_formats():
    assert parse_date("March 15, 2027").isoformat() == "2027-03-15"
    assert parse_date("2027-03-15").isoformat() == "2027-03-15"


def test_parse_date_handles_missing_or_unsupported_values():
    assert parse_date(None) is None
    assert parse_date("") is None
    assert parse_date("Spring 2027") is None


def test_pre_filter_rejects_empty_and_short_pages():
    assert not should_send_page_to_llm("")
    assert not should_send_page_to_llm("A" * 249)


def test_pre_filter_rejects_administrative_pages():
    page_text = (
        "This page contains information about our organization. "
        * 30
    )

    assert not should_send_page_to_llm(
        page_text,
        page_title="Privacy Policy",
    )


def test_pre_filter_rejects_pages_without_opportunity_indicators():
    page_text = (
        "This page describes the history of the university, "
        "its buildings, departments, and administrative structure. "
        * 10
    )

    assert not should_send_page_to_llm(page_text)


def test_pre_filter_accepts_research_opportunity_pages():
    page_text = (
        "Undergraduate Research Assistant positions are available. "
        "Students can apply to work with faculty on research projects. "
        * 10
    )

    assert should_send_page_to_llm(page_text)


def test_pre_filter_accepts_internship_pages():
    page_text = (
        "Our organization offers summer internships for university "
        "students interested in software engineering. "
        * 10
    )

    assert should_send_page_to_llm(page_text)


def test_pre_filter_accepts_opportunity_directories():
    page_text = (
        "Browse our available student positions and employment "
        "opportunities. Listings include research, internships, "
        "and co-op programs. "
        * 10
    )

    assert should_send_page_to_llm(page_text)


def test_pre_filter_accepts_indicators_in_page_title():
    page_text = (
        "Explore available programs and learn more about the "
        "application process for students. "
        * 10
    )

    assert should_send_page_to_llm(
        page_text,
        page_title="Undergraduate Research Opportunities",
    )
