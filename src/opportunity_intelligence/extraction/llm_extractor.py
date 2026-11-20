
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
You are a structured information extraction system.

Your task is to identify and extract employment, research,
internship, co-op, fellowship, and similar opportunities
from webpage content.

A webpage may contain:
- One individual position.
- One structured program offering multiple positions.
- A directory containing multiple distinct opportunities.
- General informational content that describes no actual opportunity.

YOUR MAIN TASK:

Identify every distinct opportunity explicitly described
on the webpage.

If a directory lists several opportunities, extract each
one as a separate entry in the opportunities list.

Do not combine multiple distinct opportunities into one entry.

Do not invent opportunities based on general descriptions
or references to opportunities elsewhere.

PAGE CLASSIFICATION:

Set is_opportunity_page to true if the webpage describes
at least one actual opportunity or provides a directory
of identifiable opportunities.

Set is_opportunity_page to false if the webpage only
contains general informational content.

If the page is not an opportunity page:
- Return an empty opportunities list.
- Do not invent opportunity details.

EXTRACTION RULES:

1. Extract every field explicitly supported by the webpage.
2. Do not invent information.
3. Use null for missing optional single-value fields.
4. Use empty lists when no relevant list items are provided.
5. Extract the organization offering or recruiting for each opportunity.
6. Extract the stated opportunity title.
7. Extract academic and technical subjects into field.
8. Put explicit applicant qualifications into requirements.
9. Put desirable but non-mandatory skills into preferred_skills.
10. Record compensation as stated.
11. Preserve stated durations.
12. Distinguish application deadlines from program start dates.
13. Preserve dates as written in the webpage.
14. Include short, exact evidence excerpts supporting each opportunity.
15. Do not use reasoning as a substitute for populating fields.

CATEGORIES:

Research
Internship
Co-op
Fellowship
University Employment
Government
Other

OPPORTUNITY TYPES:

Program
Individual Position
Opportunity Directory
Unknown

DIRECTORY EXTRACTION:

When a webpage contains a directory:
- Extract each identifiable opportunity separately.
- Use the individual opportunity's name as its title.
- Extract its department, organization, field, and description
  when explicitly provided.
- Do not apply details from one listing to another.
- Do not assume that every listing shares the same requirements,
  compensation, duration, or deadline.
- If a listing only provides a title and department, extract
  those details and leave unsupported fields null.
- Do not create an entry for vague references that do not identify
  a distinct opportunity.

SINGLE OPPORTUNITY EXTRACTION:

When a webpage describes one position or program:
- Return one entry in the opportunities list.
- Extract all available information about that opportunity.
- Do not create multiple entries for different details of the
  same position or program.

EVIDENCE:

Each opportunity must have its own evidence list.

Evidence must consist of short, exact excerpts copied from
the webpage that support the extracted information.

Do not use the entire webpage as evidence.

FIELD-BY-FIELD CHECK:

For every opportunity, independently inspect:
- title
- organization
- category
- opportunity_type
- field
- location
- work_mode
- description
- requirements
- preferred_skills
- compensation
- duration
- start_date
- deadline
- eligibility
- application_url

Populate every field supported by the webpage.

Do not leave a field null when its information is explicitly
available.

The reasoning field should briefly explain the overall
page classification and extraction decisions.

Return only the structured JSON response.
"""


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

    return PageExtractionResult.model_validate(response_data)
