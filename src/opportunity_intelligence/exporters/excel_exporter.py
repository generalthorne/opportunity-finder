
"""Export stored and ranked opportunities to a formatted Excel workbook."""

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from opportunity_intelligence.models import Opportunity
from opportunity_intelligence.ranking.prioritizer import (
    load_ranking_config,
    rank_opportunities
)
from opportunity_intelligence.storage.database import DEFAULT_DATABASE
from opportunity_intelligence.storage.repository import (
    count_opportunities,
    get_all_opportunities
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "opportunities.json"
)

QUALITY_REPORT_FILE = (
    PROJECT_ROOT / "data" / "processed" / "quality_report.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT / "data" / "output" / "opportunities.xlsx"
)


COLUMNS = [
    ("Title", "title"),
    ("Organization", "organization"),
    ("Category", "category"),
    ("Opportunity Type", "opportunity_type"),
    ("Fields", "field"),
    ("Location", "location"),
    ("Work Mode", "work_mode"),
    ("Description", "description"),
    ("Requirements", "requirements"),
    ("Preferred Skills", "preferred_skills"),
    ("Compensation", "compensation"),
    ("Duration", "duration"),
    ("Start Date", "start_date"),
    ("Start Date (Original)", "start_date_text"),
    ("Deadline", "deadline"),
    ("Deadline (Original)", "deadline_text"),
    ("Eligibility", "eligibility"),
    ("Status", "status"),
    ("Application URL", "application_url"),
    ("Source URL", "source_url"),
    ("Related Sources", "related_source_urls"),
    ("Evidence", "evidence"),
    ("Date Discovered", "date_discovered"),
    ("Last Verified", "last_verified"),
]


def format_value(value):
    """Convert values into readable Excel cell contents."""

    if value is None:
        return ""

    if isinstance(value, list):
        return "\n".join(str(item) for item in value)

    return str(value)


def load_json(path: Path) -> dict:
    """Load a JSON file."""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_opportunities_data(
    input_file: Path = INPUT_FILE,
    database_path: Path = DEFAULT_DATABASE
) -> dict:
    """Prefer SQLite records, falling back to the JSON export."""

    if database_path.exists():
        database_count = count_opportunities(database_path)

        if database_count > 0:
            opportunities = get_all_opportunities(database_path)

            records = [
                opportunity.model_dump(mode="json")
                for opportunity in opportunities
            ]

            return {
                "total_opportunities": len(records),
                "opportunities": records
            }

    if not input_file.exists():
        raise FileNotFoundError(
            "No opportunity data was found in SQLite or JSON."
        )

    return load_json(input_file)


def style_header(sheet, color: str):
    """Apply consistent formatting to a worksheet header."""

    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor=color
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

    sheet.row_dimensions[1].height = 32


def style_data_rows(sheet):
    """Apply consistent alignment to worksheet data."""

    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )


def build_opportunities_sheet(
    workbook: Workbook,
    opportunities_data: dict
):
    """Build the complete opportunities worksheet."""

    sheet = workbook.create_sheet("Opportunities")
    sheet.freeze_panes = "A2"

    sheet.append([label for label, _ in COLUMNS])
    style_header(sheet, "1F4E78")

    for opportunity in opportunities_data.get("opportunities", []):
        row = [
            format_value(opportunity.get(field))
            for _, field in COLUMNS
        ]
        sheet.append(row)

        for column, display_text in [
            (19, "Open Application"),
            (20, "View Source")
        ]:
            cell = sheet.cell(
                row=sheet.max_row,
                column=column
            )

            if cell.value:
                cell.hyperlink = cell.value
                cell.value = display_text
                cell.style = "Hyperlink"

    sheet.auto_filter.ref = f"A1:X{max(sheet.max_row, 1)}"
    style_data_rows(sheet)

    for index, (label, _) in enumerate(COLUMNS, start=1):
        column_letter = get_column_letter(index)

        if label in ("Description", "Requirements", "Evidence"):
            width = 45
        elif label in ("Application URL", "Source URL"):
            width = 22
        elif label == "Related Sources":
            width = 35
        elif label in ("Preferred Skills", "Eligibility"):
            width = 30
        else:
            width = 20

        sheet.column_dimensions[column_letter].width = width

    return sheet


def build_review_sheet(
    workbook: Workbook,
    quality_report: dict | None
):
    """Build the manual review worksheet."""

    sheet = workbook.create_sheet("Review Queue")
    sheet.freeze_panes = "A2"

    sheet.append([
        "Title",
        "Organization",
        "Source URL",
        "Missing Fields"
    ])

    style_header(sheet, "9C6500")

    if quality_report:
        for record in quality_report.get(
            "records_needing_review", []
        ):
            sheet.append([
                record.get("title", ""),
                record.get("organization", ""),
                record.get("source_url", ""),
                ", ".join(record.get("missing_fields", []))
            ])

    sheet.auto_filter.ref = f"A1:D{max(sheet.max_row, 1)}"
    style_data_rows(sheet)

    for column, width in {
        "A": 35,
        "B": 25,
        "C": 45,
        "D": 35
    }.items():
        sheet.column_dimensions[column].width = width

    for row in range(2, sheet.max_row + 1):
        url_cell = sheet.cell(row=row, column=3)

        if url_cell.value:
            url_cell.hyperlink = url_cell.value
            url_cell.style = "Hyperlink"

    return sheet


def build_ranked_sheet(
    workbook: Workbook,
    opportunities_data: dict,
    sheet=None
):
    """Build the ranked opportunities worksheet."""

    if sheet is None:
        sheet = workbook.create_sheet("Ranked Opportunities")

    sheet.title = "Ranked Opportunities"
    sheet.freeze_panes = "A2"

    headers = [
        "Rank",
        "Overall Score",
        "Relevance",
        "Eligibility Score",
        "Quality",
        "Deadline Score",
        "Category Preference",
        "Eligibility Status",
        "Eligibility Reason",
        "Title",
        "Organization",
        "Category",
        "Location",
        "Deadline",
        "Application",
        "Source"
    ]

    sheet.append(headers)
    style_header(sheet, "375623")

    opportunity_records = [
        Opportunity.model_validate(record)
        for record in opportunities_data.get("opportunities", [])
    ]

    config = load_ranking_config()
    ranked = rank_opportunities(opportunity_records, config)

    for rank, result in enumerate(ranked, start=1):
        opportunity = result["opportunity"]
        components = result["component_scores"]
        eligibility = result["eligibility"]

        sheet.append([
            rank,
            result["overall_score"],
            components["relevance"],
            components["eligibility"],
            components["quality"],
            components["deadline"],
            components["category_preference"],
            eligibility["status"],
            eligibility["reason"],
            opportunity.title,
            opportunity.organization,
            opportunity.category.value,
            format_value(opportunity.location),
            format_value(
                opportunity.deadline or opportunity.deadline_text
            ),
            "Open Application" if opportunity.application_url else "",
            "View Source" if opportunity.source_url else ""
        ])

        row_number = sheet.max_row

        application_cell = sheet.cell(row_number, 15)
        if opportunity.application_url:
            application_cell.hyperlink = str(
                opportunity.application_url
            )
            application_cell.style = "Hyperlink"

        source_cell = sheet.cell(row_number, 16)
        if opportunity.source_url:
            source_cell.hyperlink = str(opportunity.source_url)
            source_cell.style = "Hyperlink"

    sheet.auto_filter.ref = f"A1:P{max(sheet.max_row, 1)}"
    style_data_rows(sheet)

    for row in range(2, sheet.max_row + 1):
        for column in range(2, 8):
            sheet.cell(row, column).number_format = "0.0"

    widths = {
        "A": 9,
        "B": 15,
        "C": 13,
        "D": 17,
        "E": 13,
        "F": 15,
        "G": 20,
        "H": 20,
        "I": 45,
        "J": 35,
        "K": 25,
        "L": 22,
        "M": 22,
        "N": 22,
        "O": 20,
        "P": 20
    }

    for column, width in widths.items():
        sheet.column_dimensions[column].width = width

    return sheet


def build_source_information_sheet(
    workbook: Workbook,
    opportunities_data: dict
):
    """Build a worksheet showing where records were discovered."""

    sheet = workbook.create_sheet("Source Information")
    sheet.freeze_panes = "A2"

    headers = [
        "Title",
        "Organization",
        "Category",
        "Primary Source",
        "Related Sources",
        "Date Discovered",
        "Last Verified"
    ]

    sheet.append(headers)
    style_header(sheet, "4472C4")

    for opportunity in opportunities_data.get("opportunities", []):
        source_url = format_value(opportunity.get("source_url"))

        sheet.append([
            format_value(opportunity.get("title")),
            format_value(opportunity.get("organization")),
            format_value(opportunity.get("category")),
            "View Source" if source_url else "",
            format_value(opportunity.get("related_source_urls")),
            format_value(opportunity.get("date_discovered")),
            format_value(opportunity.get("last_verified"))
        ])

        row_number = sheet.max_row
        source_cell = sheet.cell(row_number, 4)

        if source_url:
            source_cell.hyperlink = source_url
            source_cell.style = "Hyperlink"

    sheet.auto_filter.ref = f"A1:G{max(sheet.max_row, 1)}"
    style_data_rows(sheet)

    for column, width in {
        "A": 35,
        "B": 25,
        "C": 22,
        "D": 20,
        "E": 50,
        "F": 18,
        "G": 22
    }.items():
        sheet.column_dimensions[column].width = width

    return sheet


def build_workbook(
    opportunities_data: dict,
    quality_report: dict | None = None
) -> Workbook:
    """Build the complete opportunity intelligence workbook."""

    workbook = Workbook()

    # Use the initial worksheet for the most important view.
    ranked_sheet = workbook.active
    build_ranked_sheet(
        workbook,
        opportunities_data,
        sheet=ranked_sheet
    )

    build_opportunities_sheet(workbook, opportunities_data)
    build_review_sheet(workbook, quality_report)
    build_source_information_sheet(workbook, opportunities_data)

    return workbook


def export_to_excel(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    quality_report_file: Path = QUALITY_REPORT_FILE,
    database_path: Path = DEFAULT_DATABASE
) -> Path:
    """Load stored opportunity data and export the Excel workbook."""

    opportunities_data = load_opportunities_data(
        input_file=input_file,
        database_path=database_path
    )

    quality_report = None

    if quality_report_file.exists():
        quality_report = load_json(quality_report_file)

    workbook = build_workbook(
        opportunities_data,
        quality_report
    )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    workbook.save(output_file)

    return output_file


if __name__ == "__main__":
    result = export_to_excel()
    print(f"Excel workbook created: {result}")
