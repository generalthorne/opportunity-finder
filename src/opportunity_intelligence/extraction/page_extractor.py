
"""Extract opportunities from one investigated webpage."""

from datetime import date, datetime
import logging

from pydantic import ValidationError

from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)

from opportunity_intelligence.extraction.text_preprocessor import (
    clean_page_text
)

from opportunity_intelligence.models import Opportunity


logger = logging.getLogger(__name__)


DATE_FORMATS = [
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%Y-%m-%d"
]


def parse_date(value: str | None) -> date | None:
    """Convert a supported date string into a date object."""

    if not value:
        return None

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), date_format).date()
        except ValueError:
            continue

    return None


def is_high_relevance_page(page: dict) -> bool:
    """Determine whether link analysis identified this page as relevant."""

    return (
        page.get("relevance_score", 0) >= 5
        or page.get("link_type") in {"opportunity", "directory"}
    )


def convert_extraction_to_opportunities(
    extraction_result,
    source_url: str
) -> list[Opportunity]:
    """Convert extracted records into validated Opportunity models."""

    opportunities = []

    for extracted in extraction_result.opportunities:

        if not extracted.title:
            logger.warning("Skipping opportunity without a title.")
            continue

        if not extracted.organization:
            logger.warning(
                "Skipping '%s': organization is missing.",
                extracted.title
            )
            continue

        if extracted.category is None:
            logger.warning(
                "Skipping '%s': category is missing.",
                extracted.title
            )
            continue

        opportunity_data = {
            "title": extracted.title,
            "organization": extracted.organization,
            "category": extracted.category,
            "opportunity_type": extracted.opportunity_type,
            "field": extracted.field,
            "location": extracted.location,
            "work_mode": extracted.work_mode,
            "description": extracted.description,
            "requirements": extracted.requirements,
            "preferred_skills": extracted.preferred_skills,
            "compensation": extracted.compensation,
            "duration": extracted.duration,
            "start_date": parse_date(extracted.start_date),
            "deadline": parse_date(extracted.deadline),
            "eligibility": extracted.eligibility,
            "application_url": extracted.application_url,
            "source_url": source_url,
            "evidence": extracted.evidence
        }

        try:
            opportunity = Opportunity.model_validate(opportunity_data)
            opportunities.append(opportunity)

        except ValidationError as error:
            logger.warning(
                "Skipping invalid opportunity '%s': %s",
                extracted.title,
                error
            )

    return opportunities


def extract_opportunities_from_page(
    page: dict,
    model: str | None = None,
    review_candidates: list[dict] | None = None
) -> list[Opportunity]:
    """Extract zero or more opportunities from one investigated page."""

    if page.get("status") != "success":
        return []

    page_text = page.get("page_text")

    if not isinstance(page_text, str) or not page_text.strip():
        return []

    source_url = page.get("url")

    if not source_url:
        logger.warning("Skipping page without a source URL.")
        return []

    cleaned_text = clean_page_text(page_text)

    extraction_result = extract_page_with_llm(
        page_text=cleaned_text,
        page_title=page.get("page_title"),
        model=model
    )

    if not extraction_result.is_opportunity_page:

        if not is_high_relevance_page(page):
            return []

        logger.info(
            "High-relevance page rejected by initial extraction. "
            "Retrying: %s",
            source_url
        )

        extraction_result = extract_page_with_llm(
            page_text=cleaned_text,
            page_title=page.get("page_title"),
            model=model,
            high_relevance_retry=True
        )

        if not extraction_result.is_opportunity_page:
            logger.warning(
                "High-relevance page rejected after retry. "
                "Adding to review candidates: %s",
                source_url
            )

            if review_candidates is not None:
                review_candidates.append({
                    "url": source_url,
                    "page_title": page.get("page_title"),
                    "relevance_score": page.get("relevance_score"),
                    "link_type": page.get("link_type"),
                    "matched_keywords": page.get("matched_keywords", []),
                    "discovered_in": page.get("discovered_in", []),
                    "llm_confidence": extraction_result.confidence,
                    "llm_reasoning": extraction_result.reasoning,
                    "review_reason": (
                        "High-relevance page rejected after retry."
                    )
                })

            return []

    return convert_extraction_to_opportunities(
        extraction_result=extraction_result,
        source_url=source_url
    )
