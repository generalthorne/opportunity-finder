
"""Extract structured opportunity information using a local LLM."""

import json

from opportunity_intelligence.extraction.ollama_client import (
    generate_response
)

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult,
    PageExtractionResult
)


EXTRACTION_PROMPT = """
You are an information extraction system.

Identify all distinct employment, research, internship, co-op,
fellowship, and similar opportunities described on the webpage.

PAGE CLASSIFICATION:
- Set is_opportunity_page to true if the page describes at least
  one actual opportunity or lists identifiable opportunities.
- Otherwise, set it to false and return an empty opportunities list.

EXTRACTION:
- Extract each distinct opportunity separately.
- For a single program or position, return one entry.
- For directories, return one entry per identifiable listing.
- Do not invent information or combine distinct opportunities.
- Extract only information supported by the webpage.
- Use null for missing optional values and empty lists for missing
  list values.

CATEGORIES (use exactly one):
Research, Internship, Co-op, Fellowship,
University Employment, Government, Other.

OPPORTUNITY TYPES (use exactly one):
Program, Individual Position, Opportunity Directory, Unknown.

FIELDS:
- title: opportunity name.
- organization: offering or recruiting organization.
- category and opportunity_type: classifications above.
- field: relevant academic or technical subjects.
- location and work_mode: stated location and work arrangement.
- description: concise description.
- requirements: mandatory qualifications.
- preferred_skills: desirable qualifications.
- compensation: stated pay or funding.
- duration: stated length.
- start_date and deadline: preserve dates as written.
- eligibility: stated applicant eligibility.
- application_url: application link, if provided.
- evidence: short, exact excerpts supporting the extracted details.

Do not confuse application deadlines with start dates.
Do not apply details from one directory listing to another.
Do not leave supported fields empty.

Return valid JSON matching the provided schema.
"""


def normalize_extraction_data(data: dict) -> dict:
    """Normalize common missing-value representations from the LLM."""

    missing_values = {"", "n/a", "na", "none", "null", "unknown"}

    for opportunity in data.get("opportunities", []):
        for key, value in opportunity.items():
            if isinstance(value, str) and value.strip().lower() in missing_values:
                opportunity[key] = None

    return data


def extract_page_with_llm(
    page_text: str,
    page_title: str | None = None,
    model: str | None = None
) -> PageExtractionResult:
    """Extract zero or more opportunities from one webpage."""

    if not page_text or not page_text.strip():
        raise ValueError("Page text cannot be empty.")

    prompt = f"""
{EXTRACTION_PROMPT}

Webpage title:
{page_title or "Unknown"}

Webpage content:
{page_text}
"""

    response_format = PageExtractionResult.model_json_schema()

    response_text = generate_response(
        prompt=prompt,
        model=model or "qwen3:4b",
        response_format=response_format
    )

    response_data = json.loads(response_text)

    response_data = normalize_extraction_data(response_data)

    return PageExtractionResult.model_validate(response_data)