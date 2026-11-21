import json

from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)

from opportunity_intelligence.extraction.text_preprocessor import (
    clean_page_text
)


with open(
    "data/raw/investigated_pages.json",
    "r",
    encoding="utf-8"
) as file:
    data = json.load(file)


page = data["pages"][0]

print("Running LLM extraction...", flush=True)

result = extract_page_with_llm(
    page_text=clean_page_text(page["page_text"]),
    page_title=page["page_title"]
)

print("\nEXTRACTION RESULT")
print("-----------------")
print(result.model_dump_json(indent=4))