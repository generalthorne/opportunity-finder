
"""Extract structured opportunity information using a local LLM."""

import json
import math
import re
from urllib.parse import urlsplit

from opportunity_intelligence.extraction.ollama_client import (
    generate_response
)
from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult
)


DEFAULT_MODEL = "gemma4:12b"
MAX_PAGE_CHARACTERS = 16000


EXTRACTION_PROMPT = """
You are a precise information extraction system.

Your task is to identify and extract actual employment, research,
internship, co-op, fellowship, and student program opportunities
from webpage content.

IMPORTANT: Follow the supplied JSON schema exactly.

QUALIFICATION:

A webpage qualifies if it describes at least one identifiable,
specific opportunity.

Qualifying examples:
- Named research programs and internships.
- Specific research assistant or employment positions.
- Named fellowships and student employment programs.
- Specific co-op and internship positions.

Non-qualifying examples:
- General job boards and employment portals.
- Directories that only link to other opportunities.
- Career pages without specific listings.
- Application guides, FAQs, and informational articles.
- General descriptions of an organization's research activities.

If the webpage does not describe a specific opportunity:
- Set is_opportunity_page to false.
- Return an empty opportunities list.

If the webpage describes one or more specific opportunities:
- Set is_opportunity_page to true.
- Extract each distinct opportunity separately.

CONSISTENCY:

- is_opportunity_page must be true if opportunities is non-empty.
- is_opportunity_page must be false if opportunities is empty.
- Never return false alongside a non-empty opportunities list.

EXTRACTION RULES:

- Only extract information explicitly supported by the webpage.
- Never invent information or fill gaps using assumptions.
- Extract multiple distinct opportunities separately.
- Do not duplicate the same opportunity.
- Use null for missing optional string fields.
- Use empty lists for missing list fields.
- Preserve the original wording of dates and deadlines.
- Do not confuse application deadlines with start dates.
- Do not assume an opportunity is currently accepting applications.
- Do not interpret missing information as evidence of eligibility.
- Distinguish required qualifications from preferred qualifications.
- Keep descriptions concise but informative.
- Include evidence supporting the extracted opportunity.

APPLICATION URL RULES:

- application_url must be a complete HTTP or HTTPS URL.
- Only use an actual URL found in the webpage content.
- Never use button labels or link text as a URL.
- Never return values such as "Apply online", "Click here",
  or "Application portal" as URLs.
- Do not invent URLs.
- If the actual application URL cannot be identified, return null.
- Do not substitute a general homepage or directory URL.

CATEGORIES:

Use exactly one of:
- Research
- Internship
- Co-op
- Fellowship
- University Employment
- Government
- Other

OPPORTUNITY TYPES:

Use exactly one of:
- Program
- Individual Position
- Unknown

FIELD INSTRUCTIONS:

- title: Official opportunity or position name.
- organization: Organization offering the opportunity.
- category: One of the specified categories, or null.
- opportunity_type: Program, Individual Position, or Unknown.
- field: Relevant academic or professional fields.
- location: Geographic location, if stated.
- work_mode: Remote, hybrid, on-site, or another stated arrangement.
- description: Concise description of the opportunity.
- requirements: Explicitly stated required qualifications.
- preferred_skills: Explicitly stated preferred qualifications or skills.
- compensation: Stated salary, stipend, or other compensation.
- duration: Stated length of the opportunity.
- start_date: Normalized start date, if determinable.
- deadline: Normalized application deadline, if determinable.
- start_date_text: Original wording of the start date.
- deadline_text: Original wording of the deadline.
- eligibility: Explicitly stated eligibility information.
- application_url: Actual official application URL, or null.
- evidence: Short excerpts or specific facts supporting extraction.

DATE HANDLING:

- Preserve original date wording in start_date_text and deadline_text.
- Only populate normalized dates when the date is sufficiently clear.
- Never guess a year or convert an ambiguous date into a specific date.
- Do not put an application deadline in start_date.

OUTPUT REQUIREMENTS:

- Return exactly one JSON object.
- Do not include Markdown code fences.
- Do not include introductory or concluding text.
- Follow the supplied JSON schema exactly.
- Do not add, rename, or omit schema fields.
- confidence must be a numeric value between 0 and 1.
- Use JSON null for missing optional values.
- Use empty JSON arrays for missing list values.
"""


def normalize_extraction_data(data: dict) -> dict:
    """Normalize common invalid or missing LLM output values."""

    if not isinstance(data, dict):
        raise ValueError("LLM output must be a JSON object.")

    missing_values = {
        "",
        "n/a",
        "na",
        "none",
        "null",
        "unknown",
        "not specified",
        "not available"
    }

    nullable_fields = {
        "title",
        "organization",
        "category",
        "location",
        "work_mode",
        "description",
        "compensation",
        "duration",
        "start_date",
        "deadline",
        "start_date_text",
        "deadline_text",
        "eligibility",
        "application_url"
    }

    list_fields = {
        "field",
        "requirements",
        "preferred_skills",
        "evidence"
    }

    # Normalize page-level confidence to the valid range [0, 1].
    confidence = data.get("confidence")

    try:
        if isinstance(confidence, bool):
            raise ValueError("Boolean confidence is invalid.")

        confidence = float(confidence)

        if not math.isfinite(confidence):
            confidence = 0.0

    except (TypeError, ValueError):
        confidence = 0.0

    data["confidence"] = max(0.0, min(1.0, confidence))

    opportunities = data.get("opportunities", [])

    if not isinstance(opportunities, list):
        raise ValueError("The opportunities field must be a list.")

    for opportunity in opportunities:
        if not isinstance(opportunity, dict):
            raise ValueError("Each opportunity must be a JSON object.")

        for key in nullable_fields:
            value = opportunity.get(key)

            if (
                isinstance(value, str)
                and value.strip().lower() in missing_values
            ):
                opportunity[key] = None

        for key in list_fields:
            value = opportunity.get(key)

            if value is None:
                opportunity[key] = []

            elif isinstance(value, str):
                opportunity[key] = [value] if value.strip() else []

        application_url = opportunity.get("application_url")

        if isinstance(application_url, str):
            try:
                parsed_url = urlsplit(application_url)

                if (
                    parsed_url.scheme not in {"http", "https"}
                    or not parsed_url.netloc
                ):
                    opportunity["application_url"] = None

            except ValueError:
                opportunity["application_url"] = None

    # Keep page classification consistent with extracted opportunities.
    data["is_opportunity_page"] = bool(opportunities)

    return data


def parse_llm_json(response_text: str) -> dict:
    """Parse JSON returned by the LLM."""

    if not response_text or not response_text.strip():
        raise ValueError("The LLM returned an empty response.")

    response_text = response_text.strip()

    # Remove Markdown code fences if the model ignores the prompt.
    response_text = re.sub(
        r"^```(?:json)?\s*",
        "",
        response_text,
        flags=re.IGNORECASE
    )

    response_text = re.sub(
        r"\s*```$",
        "",
        response_text
    )

    try:
        return json.loads(response_text)

    except json.JSONDecodeError as error:
        raise ValueError(
            "The LLM returned invalid JSON."
        ) from error


def extract_page_with_llm(
    page_text: str,
    page_title: str | None = None,
    model: str | None = None
) -> PageExtractionResult:
    """Extract zero or more opportunities from one webpage."""

    if not page_text or not page_text.strip():
        raise ValueError("Page text cannot be empty.")

    page_text = page_text[:MAX_PAGE_CHARACTERS]

    prompt = f"""
{EXTRACTION_PROMPT}

WEBPAGE TITLE:
{page_title or "Unknown"}

WEBPAGE CONTENT:
{page_text}
"""

    response_format = PageExtractionResult.model_json_schema()
    effective_model = model or DEFAULT_MODEL

    response_text = generate_response(
        prompt=prompt,
        model=effective_model,
        response_format=response_format
    )

    print("\n--- RAW LLM RESPONSE ---")
    print(repr(response_text))
    print("--- END RAW RESPONSE ---\n")

    response_data = parse_llm_json(response_text)
    response_data = normalize_extraction_data(response_data)

    return PageExtractionResult.model_validate(response_data)
