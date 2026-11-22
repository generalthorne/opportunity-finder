
import json
from unittest.mock import patch

from opportunity_intelligence.extraction.opportunity_extractor import (
    extract_opportunities,
    save_opportunities,
    save_quality_report
)

from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory
)

from opportunity_intelligence.extraction.opportunity_extractor import (
    deduplicate_pages,
    normalize_page_url,
)



def test_extract_opportunities_saves_quality_report(tmp_path):
    input_file = tmp_path / "investigated_pages.json"
    quality_file = tmp_path / "quality_report.json"

    input_file.write_text(
        json.dumps({"pages": []}),
        encoding="utf-8"
    )

    extract_opportunities(
        input_file=input_file,
        quality_report_file=quality_file
    )

    assert quality_file.exists()

    report = json.loads(
        quality_file.read_text(encoding="utf-8")
    )

    assert report["total_opportunities"] == 0
    assert report["opportunities_needing_review"] == 0


def test_extract_opportunities_quality_report_contains_missing_fields(
    tmp_path
):
    input_file = tmp_path / "investigated_pages.json"
    quality_file = tmp_path / "quality_report.json"

    input_file.write_text(
        json.dumps({
            "pages": [
                {
                    "status": "success",
                    "url": "https://example.com/research",
                    "page_text": "Research opportunity."
                }
            ]
        }),
        encoding="utf-8"
    )

    opportunity = Opportunity(
        title="Research Assistant",
        organization="Example University",
        category=OpportunityCategory.RESEARCH,
        source_url="https://example.com"
    )

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        return_value=[opportunity]
    ):
        extract_opportunities(
            input_file=input_file,
            quality_report_file=quality_file
        )

    report = json.loads(
        quality_file.read_text(encoding="utf-8")
    )

    assert report["total_opportunities"] == 1
    assert report["opportunities_needing_review"] == 1
    assert report["missing_field_counts"]["description"] == 1
    assert report["missing_field_counts"]["evidence"] == 1


def test_extract_opportunities_handles_empty_pages_file(tmp_path):
    input_file = tmp_path / "investigated_pages.json"

    with input_file.open("w", encoding="utf-8") as file:
        json.dump({"pages": []}, file)

    results = extract_opportunities(
        input_file=input_file,
        quality_report_file=tmp_path / "quality_report.json"
    )

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

    results = extract_opportunities(
        input_file=input_file,
        quality_report_file=tmp_path / "quality_report.json"
    )

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

    results = extract_opportunities(
        input_file=input_file,
        quality_report_file=tmp_path / "quality_report.json"
    )

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
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        return_value=[opportunity]
    ) as mock_extract:

        results = extract_opportunities(
            input_file=input_file,
            quality_report_file=tmp_path / "quality_report.json"
        )

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
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        side_effect=[[first], [second]]
    ) as mock_extract:

        results = extract_opportunities(
            input_file=input_file,
            quality_report_file=tmp_path / "quality_report.json"
        )

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
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        return_value=[]
    ) as mock_extract:

        extract_opportunities(
            input_file=input_file,
            model="qwen3:8b",
            quality_report_file=tmp_path / "quality_report.json"
        )

    assert mock_extract.call_args.kwargs["model"] == "qwen3:8b"


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
        side_effect=[
            [first_opportunity],
            RuntimeError("Extraction failed")
        ]
    ):
        results = extract_opportunities(
            input_file=input_file,
            quality_report_file=tmp_path / "quality_report.json"
        )

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
            input_file=input_file,
            max_pages=2,
            quality_report_file=tmp_path / "quality_report.json"
        )

    assert results == []
    assert mock_extract.call_count == 2


def test_extract_opportunities_processes_multiple_opportunities_from_one_page(
    tmp_path
):
    input_file = tmp_path / "investigated_pages.json"
    output_file = tmp_path / "opportunities.json"

    pages = {
        "pages": [
            {
                "status": "success",
                "url": "https://example.com/research-directory",
                "page_title": "Research Opportunities",
                "page_text": "A directory of research opportunities."
            }
        ]
    }

    with input_file.open("w", encoding="utf-8") as file:
        json.dump(pages, file)

    opportunities = [
        Opportunity(
            title="Machine Learning Research Assistant",
            organization="Example University",
            category=OpportunityCategory.RESEARCH,
            source_url="https://example.com/research-directory"
        ),
        Opportunity(
            title="Biomedical Research Program",
            organization="Example University",
            category=OpportunityCategory.RESEARCH,
            source_url="https://example.com/research-directory"
        ),
        Opportunity(
            title="Environmental Research Internship",
            organization="Example University",
            category=OpportunityCategory.INTERNSHIP,
            source_url="https://example.com/research-directory"
        )
    ]

    with patch(
        "opportunity_intelligence.extraction.opportunity_extractor."
        "extract_opportunities_from_page",
        return_value=opportunities
    ):
        results = extract_opportunities(
            input_file=input_file,
            quality_report_file=tmp_path / "quality_report.json"
        )

    save_opportunities(results, output_file)

    assert len(results) == 3

    with output_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["total_opportunities"] == 3
    assert len(data["opportunities"]) == 3


def test_normalize_page_url_removes_fragments_and_trailing_slashes():
    assert normalize_page_url(
        "https://example.com/research/#section"
    ) == "https://example.com/research"

    assert normalize_page_url(
        "https://example.com/research/"
    ) == "https://example.com/research"


def test_deduplicate_pages_removes_duplicate_urls():
    pages = [
        {
            "url": "https://example.com/research",
            "status": "success",
            "page_text": "Research opportunity information."
        },
        {
            "url": "https://example.com/research/#section",
            "status": "success",
            "page_text": "Duplicate page."
        },
        {
            "url": "https://example.com/internships",
            "status": "success",
            "page_text": "Internship information."
        }
    ]

    results = deduplicate_pages(pages)

    assert len(results) == 2
    assert results[0]["url"] == "https://example.com/research"
    assert results[1]["url"] == "https://example.com/internships"


def test_deduplicate_pages_keeps_most_complete_successful_page():
    pages = [
        {
            "url": "https://example.com/research",
            "status": "success",
            "page_text": "Short text."
        },
        {
            "url": "https://example.com/research/",
            "status": "success",
            "page_text": "Much more complete research opportunity information."
        }
    ]

    results = deduplicate_pages(pages)

    assert len(results) == 1
    assert results[0]["page_text"].startswith("Much more complete")


def test_deduplicate_pages_prefers_successful_page():
    pages = [
        {
            "url": "https://example.com/research",
            "status": "failed",
            "page_text": None
        },
        {
            "url": "https://example.com/research/",
            "status": "success",
            "page_text": "Research opportunity information."
        }
    ]

    results = deduplicate_pages(pages)

    assert len(results) == 1
    assert results[0]["status"] == "success"


def test_deduplicate_pages_keeps_pages_without_urls():
    pages = [
        {"status": "success", "page_text": "Page one."},
        {"status": "success", "page_text": "Page two."}
    ]

    results = deduplicate_pages(pages)

    assert len(results) == 2
