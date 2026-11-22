
import json
import ollama

from opportunity_intelligence.extraction.extraction_result import PageExtractionResult

with open("data/raw/investigated_pages.json", encoding="utf-8") as file:
    data = json.load(file)

page = data["pages"][75]

prompt = f"""
Extract the following webpage into a JSON object.

Include:
- is_opportunity_page
- confidence
- opportunities

Return one valid JSON object only. Do not include Markdown or explanatory text.

Title:
{page.get("page_title")}

Content:
{page.get("page_text", "")[:16000]}
"""

print("Testing:", page["url"])
print("Prompt length:", len(prompt))

response = ollama.chat(
    model="gemma4:12b",
    messages=[{"role": "user", "content": prompt}],
    think=False,
    format=PageExtractionResult.model_json_schema(),
    options={"temperature": 0},
)

print("\nResponse:")
print(response.model_dump_json(indent=2))

print("\nDone:", response.done)
print("Done reason:", response.done_reason)
print("Response length:", len(response.message.content))
print("Raw content:", repr(response.message.content))



try:
    parsed = json.loads(response.message.content)
    validated = PageExtractionResult.model_validate(parsed)

    print("\nPydantic validation: PASSED")
    print(validated.model_dump_json(indent=2))

except Exception as e:
    print("\nPydantic validation: FAILED")
    print(e)
