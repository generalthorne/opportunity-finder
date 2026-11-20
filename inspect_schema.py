
import json

from opportunity_intelligence.extraction.extraction_result import (
    OpportunityExtractionResult
)

schema = OpportunityExtractionResult.model_json_schema()

print(json.dumps(schema, indent=4))
