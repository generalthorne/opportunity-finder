
import pytest
from openpyxl import load_workbook

from opportunity_intelligence.exporters.excel_exporter import (
    build_workbook,
    export_to_excel
)


@pytest.fixture
def sample_opportunity_data():
    return {
        "total_opportunities": 1,
        "opportunities": [
            {
                "title": "Undergraduate Research Assistant",
                "organization": "University of Toronto",
                "category": "Research",
                "opportunity_type": "Individual Position",
                "field": ["Computer Science", "Machine Learning"],
                "location": "Toronto, Canada",
                "work_mode": "On-site",
                "description": "Assist with a machine learning research project.",
                "evidence": ["The page identifies this as a research position."],
                "requirements": ["Programming experience"],
                "preferred_skills": ["Python"],
                "compensation": "Paid",
                "duration": "Summer",
                "start_date": None,
                "deadline": None,
                "start_date_text": "May 2027",
                "deadline_text": "Applications close in February",
                "eligibility": "Undergraduate students",
                "application_url": "https://example.com/apply",
                "source_url": "https://example.com/source",
                "related_source_urls": [],
                "date_discovered": "2026-11-21",
                "last_verified": None,
                "status": "Open"
            }
        ]
    }


@pytest.fixture
def sample_quality_report():
    return {
        "total_opportunities": 1,
        "opportunities_needing_review": 1,
        "missing_field_counts": {
            "deadline": 1
        },
        "records_needing_review": [
            {
                "title": "Undergraduate Research Assistant",
                "organization": "University of Toronto",
                "source_url": "https://example.com/source",
                "missing_fields": ["deadline"]
            }
        ]
    }


def test_build_workbook_creates_both_sheets(
    sample_opportunity_data,
    sample_quality_report
):
    workbook = build_workbook(
        sample_opportunity_data,
        sample_quality_report
    )

    assert workbook.sheetnames == [
        "Ranked Opportunities",
        "Opportunities",
        "Review Queue",
        "Source Information"
    ]


def test_build_workbook_includes_opportunity_data(
    sample_opportunity_data
):
    workbook = build_workbook(sample_opportunity_data)
    sheet = workbook["Opportunities"]

    assert sheet["A2"].value == "Undergraduate Research Assistant"
    assert sheet["B2"].value == "University of Toronto"
    assert sheet["C2"].value == "Research"


def test_build_workbook_formats_hyperlinks(
    sample_opportunity_data
):
    workbook = build_workbook(sample_opportunity_data)
    sheet = workbook["Opportunities"]

    assert sheet["S2"].value == "Open Application"
    assert sheet["S2"].hyperlink.target == "https://example.com/apply"

    assert sheet["T2"].value == "View Source"
    assert sheet["T2"].hyperlink.target == "https://example.com/source"

    assert sheet["S2"].alignment.vertical == "top"
    assert sheet["T2"].alignment.vertical == "top"


def test_build_workbook_includes_review_queue(
    sample_opportunity_data,
    sample_quality_report
):
    workbook = build_workbook(
        sample_opportunity_data,
        sample_quality_report
    )
    sheet = workbook["Review Queue"]

    assert sheet["A2"].value == "Undergraduate Research Assistant"
    assert sheet["D2"].value == "deadline"


def test_export_to_excel_creates_file(
    tmp_path,
    sample_opportunity_data,
    sample_quality_report
):
    import json

    input_file = tmp_path / "opportunities.json"
    quality_file = tmp_path / "quality_report.json"
    output_file = tmp_path / "opportunities.xlsx"

    input_file.write_text(
        json.dumps(sample_opportunity_data),
        encoding="utf-8"
    )
    quality_file.write_text(
        json.dumps(sample_quality_report),
        encoding="utf-8"
    )

    result = export_to_excel(
        input_file=input_file,
        output_file=output_file,
        quality_report_file=quality_file
    )

    assert result == output_file
    assert output_file.exists()

    workbook = load_workbook(output_file)
    assert workbook.sheetnames == [
        "Ranked Opportunities",
        "Opportunities",
        "Review Queue",
        "Source Information"
    ]
