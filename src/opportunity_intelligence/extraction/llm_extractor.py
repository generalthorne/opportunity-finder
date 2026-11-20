
"""Extract structured opportunity information using a local LLM."""

import json

from opportunity_intelligence.extraction.ollama_client import (
    generate_response
)

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult
)



EXTRACTION_PROMPT = """
You are a structured information extraction system.

Your task is to extract information about employment, research,
internship, co-op, fellowship, and similar opportunities from
webpage content.

First, determine whether the webpage describes an actual opportunity.

An opportunity may be:
- A specific individual position.
- A structured program offering multiple positions.
- A directory containing multiple opportunities.

Do not classify ordinary informational pages as opportunities.

EXTRACTION RULES:

1. Extract every field that is explicitly supported by the webpage.
2. Do not leave a field empty if the information is clearly stated.
3. Do not invent information that is not present.
4. Use null for missing optional single-value fields.
5. Use empty lists only when no relevant list items are provided.
6. Extract the organization from statements identifying who offers,
   operates, or recruits for the opportunity.
7. Extract the opportunity title from the page title or the
   opportunity's stated name.
8. Extract academic and technical subjects into the field list.
9. Put explicit applicant qualifications into requirements.
10. Record compensation exactly as described, such as "Paid".
11. Preserve stated durations, such as "12 weeks".
12. Distinguish application deadlines from program start dates.
13. Preserve dates as written in the webpage.
14. Include short, exact evidence excerpts from the webpage.
15. Do not use reasoning as a substitute for populating fields.

The evidence list should contain short excerpts directly copied
from the webpage that support the extracted information.

The category must be one of:
Research
Internship
Co-op
Fellowship
University Employment
Government
Other

The opportunity_type must be one of:
Program
Individual Position
Opportunity Directory
Unknown

If the page does not describe an opportunity:
- Set is_opportunity to false.
- Do not invent opportunity details.


FIELD-BY-FIELD EXTRACTION:

For every webpage, inspect each field independently.

Before returning the result, check the following:

- title: What is the name of the opportunity?
- organization: Which organization offers or recruits for it?
- field: What academic, technical, or professional subjects are mentioned?
- requirements: What qualifications or conditions must applicants meet?
- preferred_skills: What skills are desirable but not mandatory?
- compensation: Is the position paid, unpaid, or does it provide a stated amount?
- duration: How long does the opportunity last?
- start_date: When does the opportunity begin?
- deadline: When must applications be submitted?
- eligibility: Who is permitted to apply?
- application_url: Is an application link explicitly provided?

IMPORTANT:

Evidence excerpts are not substitutes for extracted fields.

If a fact appears in the webpage, populate its corresponding
field even if that fact is also included in the evidence list.

For example:

Webpage:
"The University of Example is recruiting undergraduate students
for a summer research assistant position. The position is paid
and lasts 12 weeks. Applications close March 15, 2027."

Expected extraction:
- title: "Summer Research Assistant Position"
- organization: "University of Example"
- compensation: "Paid"
- duration: "12 weeks"
- deadline: "March 15, 2027"

Do not leave these fields null when the information is explicitly
available.

"""



def extract_page_with_llm(
    page_text: str,
    page_title: str | None = None,
    model: str | None = None
) -> OpportunityExtractionResult:
    """Extract structured opportunity information from webpage text."""

    if not page_text or not page_text.strip():
        raise ValueError("Page text cannot be empty.")

    prompt = f"""
{EXTRACTION_PROMPT}

Webpage title:
{page_title or "Unknown"}

Webpage content:
{page_text}
"""

    response_format = OpportunityExtractionResult.model_json_schema()

    response_text = generate_response(
        prompt=prompt,
        model=model or "qwen3:4b",
        response_format=response_format
    )

    response_data = json.loads(response_text)

    return OpportunityExtractionResult.model_validate(response_data)
