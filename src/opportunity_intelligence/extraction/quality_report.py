
"""Generate quality reports for extracted opportunities."""

from opportunity_intelligence.models import Opportunity


FIELDS_TO_CHECK = [
    "description",
    "location",
    "eligibility",
    "requirements",
    "deadline",
    "application_url",
    "evidence"
]


def is_missing(value) -> bool:
    """Determine whether an extracted field is missing."""

    if value is None:
        return True

    if isinstance(value, str):
        return not value.strip()

    if isinstance(value, list):
        return len(value) == 0

    return False


def build_quality_report(
    opportunities: list[Opportunity]
) -> dict:
    """Summarize missing information across extracted opportunities."""

    total = len(opportunities)

    missing_field_counts = {
        field: 0
        for field in FIELDS_TO_CHECK
    }

    records_needing_review = []

    for opportunity in opportunities:
        missing_fields = []

        for field in FIELDS_TO_CHECK:
            value = getattr(opportunity, field)

            if field == "deadline":
                value = value or opportunity.deadline_text

            if is_missing(value):
                missing_field_counts[field] += 1
                missing_fields.append(field)

        if missing_fields:
            records_needing_review.append({
                "title": opportunity.title,
                "organization": opportunity.organization,
                "source_url": str(opportunity.source_url),
                "missing_fields": missing_fields
            })

    return {
        "total_opportunities": total,
        "opportunities_needing_review": len(
            records_needing_review
        ),
        "missing_field_counts": missing_field_counts,
        "records_needing_review": records_needing_review
    }


