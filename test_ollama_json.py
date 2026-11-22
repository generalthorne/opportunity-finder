
import json

from opportunity_intelligence.extraction.ollama_client import (
    generate_response,
)
from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult,
)


schema = PageExtractionResult.model_json_schema()

prompt = """
Return exactly this JSON structure, following the supplied schema.

There are no opportunities on this page.

Return:
{
    "is_opportunity_page": false,
    "opportunities": []
}
"""

print("Testing Ollama structured JSON output...")

response = generate_response(
    prompt=prompt,
    model="qwen3:8b",
    response_format=schema,
)

print("\nRaw response:")
print(repr(response))

print("\nJSON validation:")

try:
    parsed = json.loads(response)
    validated = PageExtractionResult.model_validate(parsed)

    print("SUCCESS: Valid JSON and schema.")
    print(validated.model_dump_json(indent=2))

except json.JSONDecodeError as error:
    print("FAILED: Invalid JSON.")
    print(error)

except Exception as error:
    print("FAILED: Schema validation.")
    print(type(error).__name__, error)
