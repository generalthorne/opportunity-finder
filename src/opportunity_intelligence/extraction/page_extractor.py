
"""Extract opportunities from one investigated webpage."""

import calendar
import logging
from datetime import date, datetime

from pydantic import ValidationError

from opportunity_intelligence.extraction.extraction_cache import (
    ExtractionCache,
    calculate_content_hash,
)
from opportunity_intelligence.extraction.llm_extractor import (
    DEFAULT_MODEL,
    extract_page_with_llm,
)
from opportunity_intelligence.extraction.text_preprocessor import (
    clean_page_text,
    prepare_page_text,
)
from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
)

logger = logging.getLogger(__name__)


MINIMUM_PAGE_TEXT_LENGTH = 250


EXCLUDED_PAGE_TITLE_TERMS = (
    "privacy policy",
    "terms of use",
    "terms and conditions",
    "cookie policy",
    "accessibility statement",
    "contact us",
    "contact information",
    "sign in",
    "log in",
    "login",
    "password reset",
    "site map",
    "sitemap",
)


OPPORTUNITY_INDICATORS = (
    "research opportunity",
    "research assistant",
    "research position",
    "undergraduate research",
    "summer research",
    "internship",
    "internships",
    "intern",
    "co-op",
    "coop",
    "pey",
    "fellowship",
    "fellowships",
    "student employment",
    "student jobs",
    "student position",
    "student positions",
    "student program",
    "student programs",
    "employment opportunity",
    "employment opportunities",
    "job opportunity",
    "job opportunities",
    "job posting",
    "job postings",
    "career opportunity",
    "career opportunities",
    "open position",
    "open positions",
    "hiring",
)


DATE_FORMATS = [
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
]


def should_send_page_to_llm(
    page_text: str,
    page_title: str | None = None,
) -> bool:
    """Decide whether a webpage is worth sending to the LLM."""

    if not isinstance(page_text, str):
        return False

    text = page_text.strip()

    if len(text) < MINIMUM_PAGE_TEXT_LENGTH:
        return False

    title = (page_title or "").strip().lower()

    if any(term in title for term in EXCLUDED_PAGE_TITLE_TERMS):
        return False

    searchable_content = f"{title}\n{text}".lower()

    if not any(
        indicator in searchable_content
        for indicator in OPPORTUNITY_INDICATORS
    ):
        return False

    return True


def parse_date(value: str | None, is_deadline: bool = False) -> date | None:
    """Parse supported date formats."""

    if not value:
        return None

    value = value.strip()

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            continue

    for date_format in ("%B %Y", "%b %Y"):
        try:
            parsed = datetime.strptime(value, date_format).date()

            if is_deadline:
                last_day = calendar.monthrange(
                    parsed.year,
                    parsed.month,
                )[1]
                return date(parsed.year, parsed.month, last_day)

            return date(parsed.year, parsed.month, 1)

        except ValueError:
            continue

    return None


def is_qualified_opportunity(extracted) -> bool:
    """Reject directories and generic opportunity portals."""

    title = (extracted.title or "").strip().lower()
    description = (extracted.description or "").lower()

    if not title or not extracted.organization:
        return False

    if extracted.opportunity_type == "Opportunity Directory":
        return False

    generic_titles = {
        "federal internships",
        "internship opportunities",
        "research opportunities",
        "student opportunities",
        "job opportunities",
        "career opportunities",
        "employment opportunities",
        "undergraduate opportunities",
    }

    if title in generic_titles:
        return False

    generic_terms = (
        "job board",
        "employment portal",
        "opportunity directory",
        "job search portal",
    )

    if any(term in title or term in description for term in generic_terms):
        return False

    return True


def correct_category(extracted) -> OpportunityCategory:
    """Correct obvious category misclassifications."""

    title = (extracted.title or "").lower()
    description = (extracted.description or "").lower()

    if "co-op" in title or "coop" in title or "pey" in title:
        return OpportunityCategory.COOP

    if "internship" in title or "intern" in title:
        return OpportunityCategory.INTERNSHIP

    if "fellowship" in title:
        return OpportunityCategory.FELLOWSHIP

    if "research" in title or "research" in description:
        return OpportunityCategory.RESEARCH

    return extracted.category


def determine_status(deadline: date | None) -> OpportunityStatus:
    """Determine application status from a known deadline."""

    if deadline is None:
        return OpportunityStatus.UNKNOWN

    if deadline < date.today():
        return OpportunityStatus.CLOSED

    return OpportunityStatus.OPEN


def convert_extraction_to_opportunities(
    extraction_result,
    source_url: str,
) -> list[Opportunity]:
    """Convert extracted records into validated Opportunity models."""

    opportunities = []

    for extracted in extraction_result.opportunities:
        if not is_qualified_opportunity(extracted):
            continue

        if extracted.category is None:
            continue

        start_date = parse_date(extracted.start_date)
        deadline = parse_date(extracted.deadline, is_deadline=True)

        opportunity_data = {
            "title": extracted.title,
            "organization": extracted.organization,
            "category": correct_category(extracted),
            "opportunity_type": (
                extracted.opportunity_type
                if extracted.opportunity_type in {
                    "Program",
                    "Individual Position",
                    "Unknown",
                }
                else "Unknown"
            ),
            "field": extracted.field,
            "location": extracted.location,
            "work_mode": extracted.work_mode,
            "description": extracted.description,
            "requirements": extracted.requirements,
            "preferred_skills": extracted.preferred_skills,
            "compensation": extracted.compensation,
            "duration": extracted.duration,
            "start_date": start_date,
            "deadline": deadline,
            "start_date_text": (
                extracted.start_date_text or extracted.start_date
            ),
            "deadline_text": (
                extracted.deadline_text or extracted.deadline
            ),
            "eligibility": extracted.eligibility,
            "application_url": extracted.application_url,
            "source_url": source_url,
            "evidence": extracted.evidence,
            "status": determine_status(deadline),
        }

        try:
            opportunity = Opportunity.model_validate(opportunity_data)
            opportunities.append(opportunity)

        except ValidationError as error:
            logger.warning(
                "Skipping invalid opportunity '%s': %s",
                extracted.title,
                error,
            )

    return opportunities


def extract_opportunities_from_page(
    page: dict,
    model: str | None = None,
    cache: ExtractionCache | None = None,
) -> list[Opportunity]:
    """Extract zero or more opportunities from one investigated page."""

    if page.get("status") != "success":
        return []

    page_text = page.get("page_text")

    if not isinstance(page_text, str) or not page_text.strip():
        return []

    source_url = page.get("url")

    if not isinstance(source_url, str) or not source_url.strip():
        logger.warning("Skipping page without a valid source URL.")
        return []

    page_title = page.get("page_title")

    # Clean the full page before preliminary screening.
    cleaned_text = clean_page_text(page_text)

    if not should_send_page_to_llm(
        page_text=cleaned_text,
        page_title=page_title,
    ):
        logger.info(
            "Skipping LLM extraction: page did not pass preliminary "
            "opportunity screening. URL: %s",
            source_url,
        )
        return []

    # Prioritize relevant sections and enforce the LLM input limit.
    llm_text = prepare_page_text(cleaned_text)

    logger.info(
        "Prepared LLM input: %d characters (reduced from %d). URL: %s",
        len(llm_text),
        len(cleaned_text),
        source_url,
    )

    if not llm_text.strip():
        return []

    effective_model = model or DEFAULT_MODEL

    # Cache the exact text that will be sent to the LLM.
    content_hash = calculate_content_hash(
        page_text=llm_text,
        page_title=page_title,
    )

    extraction_result = None

    if cache is not None:
        extraction_result = cache.get(
            url=source_url,
            content_hash=content_hash,
            model=effective_model,
        )

        if extraction_result is not None:
            logger.info(
                "Using cached extraction result. URL: %s",
                source_url,
            )

    if extraction_result is None:
        logger.info(
            "Running LLM extraction. Model: %s. URL: %s",
            effective_model,
            source_url,
        )

        extraction_result = extract_page_with_llm(
            page_text=llm_text,
            page_title=page_title,
            model=effective_model,
        )

        if cache is not None:
            cache.set(
                url=source_url,
                content_hash=content_hash,
                model=effective_model,
                result=extraction_result,
            )

    if not extraction_result.is_opportunity_page:
        return []

    return convert_extraction_to_opportunities(
        extraction_result=extraction_result,
        source_url=source_url,
    )
