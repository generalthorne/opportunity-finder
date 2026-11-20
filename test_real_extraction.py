
from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)


page_text = """
The University of Example maintains a directory of undergraduate
research opportunities.

Available opportunities include:

1. Machine Learning Research Assistant
   Department: Computer Science
   Students work on machine learning projects with faculty members.

2. Biomedical Research Summer Program
   Department: Biology
   Students participate in supervised biomedical research.

3. Environmental Research Internship
   Department: Environmental Science
   Students assist with ongoing environmental research projects.

Students should review individual opportunity pages for
application requirements, deadlines, and additional details.
"""


result = extract_page_with_llm(
    page_text=page_text,
    page_title="Undergraduate Research Opportunities Directory"
)

print("\nEXTRACTION RESULT")
print("-----------------")

print(result.model_dump_json(indent=4))
