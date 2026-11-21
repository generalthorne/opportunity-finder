import json

from unittest.mock import patch

from opportunity_intelligence.extraction.opportunity_extractor import (
    extract_opportunities,
    save_opportunities
)

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory
)


def test_extract_opportunities_handles_empty_pages_file(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    with input_file.open("w", encoding="utf-8") as file:
        json.dump({"pages": []}, file)

    results = extract_opportunities(input_file)

    assert results == []


def test_extract_opportunities_handles_failed_pages(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {
                "status": "failed",
                "url": "https://example.com/failed",
                "page_text": None
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    results = extract_opportunities(input_file)

    assert results == []


def test_extract_opportunities_handles_empty_page_text(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {
                "status": "success",
                "url": "https://example.com/empty",
                "page_text": ""
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    results = extract_opportunities(input_file)

    assert results == []


def test_save_opportunities(tmp_path):
    output_file = tmp_path / "opportunities.json"

    opportunity = Opportunity(
        title="Undergraduate Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        source_url="https://example.com/research"
    )

    save_opportunities([opportunity], output_file)

    assert output_file.exists()

    with output_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["total_opportunities"] == 1
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["title"] == (
        "Undergraduate Research Assistant"
    )


def test_extract_opportunities_processes_successful_pages(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {
                "status": "success",
                "url": "https://example.com/research",
                "page_title": "Research",
                "page_text": "Research opportunity."
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    opportunity = Opportunity(
        title="Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        source_url="https://example.com/research"
    )

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor.extract_opportunities_from_page",
        return_value=[opportunity]
    ) as mock_extract:

        results = extract_opportunities(input_file)

    assert len(results) == 1
    assert results[0].title == "Research Assistant"
    mock_extract.assert_called_once()


def test_extract_opportunities_processes_multiple_pages(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {
                "status": "success",
                "url": "https://example.com/research",
                "page_text": "Research opportunity."
            },
            {
                "status": "success",
                "url": "https://example.com/internship",
                "page_text": "Internship opportunity."
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    first = Opportunity(
        title="Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        source_url="https://example.com/research"
    )

    second = Opportunity(
        title="Software Engineering Intern",
        organization="Example Company",
        category=OpportunityCategory.INTERNSHIP,
        source_url="https://example.com/internship"
    )

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor.extract_opportunities_from_page",
        side_effect=[[first], [second]]
    ) as mock_extract:

        results = extract_opportunities(input_file)

    assert len(results) == 2
    assert mock_extract.call_count == 2


def test_extract_opportunities_passes_model_to_page_extractor(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {
                "status": "success",
                "url": "https://example.com/research",
                "page_text": "Research opportunity."
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor.extract_opportunities_from_page",
        return_value=[]
    ) as mock_extract:

        extract_opportunities(
            input_file,
            model="qwen3:4b"
        )

    assert mock_extract.call_args.kwargs["model"] == "qwen3:4b"



def test_extract_opportunities_continues_after_page_failure(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {"url": "https://example.com/1", "status": "success"},
            {"url": "https://example.com/2", "status": "success"}
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    first_opportunity = Opportunity(
        title="Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        source_url="https://example.com/1"
    )

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        side_effect=[[first_opportunity], RuntimeError("Extraction failed")]
    ):
        results = extract_opportunities(input_file)

    assert len(results) == 1
    assert results[0] == first_opportunity


def test_extract_opportunities_respects_max_pages(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    pages = {
        "pages": [
            {"url": "https://example.com/1", "status": "success"},
            {"url": "https://example.com/2", "status": "success"},
            {"url": "https://example.com/3", "status": "success"}
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        return_value=[]
    ) as mock_extract:

        results = extract_opportunities(
            input_file,
            max_pages=2
        )

    assert results == []
    assert mock_extract.call_count == 2
