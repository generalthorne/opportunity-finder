import json

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