
"""Extract structured opportunity information using a local LLM."""

import json

from opportunity_intelligence.extraction.ollama_client import (
    generate_response
)

from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult
)




EXTRACTION_PROMPT = """
You are an information extraction system.

Your task is to identify actual, specific employment, research,
internship, co-op, fellowship, and student program opportunities.

QUALIFICATION RULES:

A qualifying opportunity must be a specific named
program, position, fellowship, internship, co-op, or employment opportunity.

DO NOT treat the following as opportunities:
- General job-search websites or employment portals.
- General internship or research directories.
- Career pages that only link to other opportunities.
- General application guides, FAQs, or instructions.
- General descriptions of research or employment services.
- News articles or informational resources.

A directory may contain individual opportunities. Extract an
individual listing only when the webpage provides enough information
to identify that specific opportunity.

If the page does not describe an actual specific opportunity:
- Set is_opportunity_page to false.
- Return an empty opportunities list.

EXTRACTION RULES:

- Extract each distinct qualifying opportunity separately.
- Never create an opportunity from a general portal or directory.
- Do not invent information or combine distinct opportunities.
- Only extract details supported by the webpage.
- Use null for missing optional values.
- Use empty lists for missing list values.
- Preserve original date wording.

CATEGORIES (use exactly one):
Research, Internship, Co-op, Fellowship,
University Employment, Government, Other.

OPPORTUNITY TYPES (use exactly one):
Program, Individual Position, Unknown.

FIELDS:

- title: Exact opportunity or program name.
- organization: Offering or recruiting organization.
- category: Best-fitting category.
- opportunity_type: Program, Individual Position, or Unknown.
- field: Relevant academic or technical subjects.
- location: Stated location.
- work_mode: Stated work arrangement.
- description: Concise description.
- requirements: Mandatory qualifications.
- preferred_skills: Desirable qualifications.
- compensation: Stated pay or funding.
- duration: Stated length.
- start_date: Start date, preserved as written.
- deadline: Application deadline, preserved as written.
- start_date_text: Original start date wording.
- deadline_text: Original deadline wording.
- eligibility: Stated applicant eligibility.
- application_url: Direct official application link, if available.
- evidence: Short exact excerpts supporting extracted details.

IMPORTANT:

- Do not confuse application deadlines with start dates.
- Do not use a general organization homepage as an application URL.
- Do not use a directory URL as an application URL.
- Do not invent an application URL.
- Do not assume an opportunity is currently open.
- Do not interpret missing information as evidence of eligibility.

Return valid JSON matching the provided schema.
"""





HIGH_RELEVANCE_RETRY_INSTRUCTIONS = """
IMPORTANT: REASSESS THE PAGE CLASSIFICATION.

This webpage was independently identified as highly relevant by
a separate link-analysis stage. Your initial classification may
have been too restrictive.

Check carefully for:
- Named research programs, internships, co-op programs, fellowships,
  student employment positions, and similar opportunities.
- Opportunities restricted to a particular university, faculty,
  department, academic year, or student group.
- Programs that are described on informational or application pages.
- Individual opportunities listed within a directory.

Eligibility restrictions do NOT mean that something is not an
opportunity. Do not reject a program merely because it is limited
to a specific group of students.

If the page identifies or describes an actual opportunity, set
is_opportunity_page to true and extract the supported details.

However, do not invent opportunities. If the page contains only
general information and does not identify or describe an actual
opportunity, set is_opportunity_page to false.

Return valid JSON matching the provided schema.
"""


def normalize_extraction_data(data: dict) -> dict:
    """Normalize common missing-value representations from the LLM."""

    missing_values = {"", "n/a", "na", "none", "null", "unknown"}

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
        "eligibility",
        "application_url"
    }

    for opportunity in data.get("opportunities", []):
        for key in nullable_fields:
            value = opportunity.get(key)

            if (
                isinstance(value, str)
                and value.strip().lower() in missing_values
            ):
                opportunity[key] = None

    return data


def extract_page_with_llm(
    page_text: str,
    page_title: str | None = None,
    model: str | None = None,
    high_relevance_retry: bool = False
) -> PageExtractionResult:
    """Extract zero or more opportunities from one webpage."""

    # Limit input size to prevent excessively slow LLM requests.
    max_characters = 16000
    page_text = page_text[:max_characters]

    if not page_text or not page_text.strip():
        raise ValueError("Page text cannot be empty.")

    retry_instructions = (
        HIGH_RELEVANCE_RETRY_INSTRUCTIONS
        if high_relevance_retry
        else ""
    )

    prompt = f"""
{EXTRACTION_PROMPT}

{retry_instructions}

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

    try:
        response_data = json.loads(response_text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "The LLM returned invalid JSON."
        ) from error

    response_data = normalize_extraction_data(response_data)

    return PageExtractionResult.model_validate(response_data)
