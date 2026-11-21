
"""Export extracted opportunities to a formatted Excel workbook."""

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "opportunities.json"
)

QUALITY_REPORT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "quality_report.json"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "opportunities.xlsx"
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


def build_workbook(
    opportunities_data: dict,
    quality_report: dict | None = None
) -> Workbook:
    """Build a formatted workbook from extracted opportunities."""

    workbook = Workbook()

    # Main opportunities sheet.
    sheet = workbook.active
    sheet.title = "Opportunities"
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = "A1:X1"

    headers = [label for label, _ in COLUMNS]
    sheet.append(headers)

    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78"
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

    for opportunity in opportunities_data.get("opportunities", []):
        row = [
            format_value(opportunity.get(field))
            for _, field in COLUMNS
        ]
        sheet.append(row)

        for cell in sheet[sheet.max_row]:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )

        # Make application and source URLs clickable.
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
                cell.alignment = Alignment(
                    vertical="top",
                    wrap_text=True
                )
        sheet.row_dimensions[1].height = 32

    # Set practical column widths.
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

    # Review queue sheet.
    review_sheet = workbook.create_sheet("Review Queue")
    review_sheet.freeze_panes = "A2"

    review_headers = [
        "Title",
        "Organization",
        "Source URL",
        "Missing Fields"
    ]
    review_sheet.append(review_headers)

    for cell in review_sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="9C6500"
        )
        cell.alignment = Alignment(wrap_text=True)

    if quality_report:
        for record in quality_report.get(
            "records_needing_review", []
        ):
            review_sheet.append([
                record.get("title", ""),
                record.get("organization", ""),
                record.get("source_url", ""),
                ", ".join(record.get("missing_fields", []))
            ])

    review_sheet.auto_filter.ref = (
        f"A1:D{max(review_sheet.max_row, 1)}"
    )

    for column, width in {
        "A": 35,
        "B": 25,
        "C": 45,
        "D": 35
    }.items():
        review_sheet.column_dimensions[column].width = width

    for row in review_sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True
            )

    for row in range(2, review_sheet.max_row + 1):
        url_cell = review_sheet.cell(row=row, column=3)
        if url_cell.value:
            url_cell.hyperlink = url_cell.value
            url_cell.style = "Hyperlink"

    return workbook


def export_to_excel(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    quality_report_file: Path = QUALITY_REPORT_FILE
) -> Path:
    """Load project data and export it to Excel."""

    opportunities_data = load_json(input_file)

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
