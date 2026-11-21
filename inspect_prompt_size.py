import json

from opportunity_intelligence.extraction.llm_extractor import (
    EXTRACTION_PROMPT
)
from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult
)

with open("data/raw/investigated_pages.json", encoding="utf-8") as file:
    data = json.load(file)

page = data["pages"][0]

prompt = f"""
{EXTRACTION_PROMPT}

Webpage title:
{page["page_title"]}

Webpage content:
{page["page_text"]}
"""

schema = PageExtractionResult.model_json_schema()

print("EXTRACTION PROMPT")
print("Characters:", len(prompt))

print("\nJSON SCHEMA")
print("Characters:", len(json.dumps(schema)))

print("\nCOMBINED SIZE")
print("Characters:", len(prompt) + len(json.dumps(schema)))