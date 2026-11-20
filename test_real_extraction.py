
from opportunity_intelligence.extraction.llm_extractor import (
    extract_page_with_llm
)


page_text = """
The University of Example offers the Summer Undergraduate Research Program
for undergraduate students interested in gaining research experience.

The program runs for 12 weeks during the summer. Participants work under
the supervision of university faculty members and contribute to ongoing
research projects.

Research areas available through the program include:

1. Computer Science
   Students may work on artificial intelligence, machine learning,
   and software systems research.

2. Biology
   Students may participate in biomedical and molecular biology research.

3. Environmental Science
   Students may contribute to environmental monitoring and sustainability
   research projects.

Applicants must be currently enrolled undergraduate students.

Students apply to the Summer Undergraduate Research Program through
a single application. Research placements are assigned based on
student interests and faculty availability.
"""


result = extract_page_with_llm(
    page_text=page_text,
    page_title="Summer Undergraduate Research Program"
)


print("\nEXTRACTION RESULT")
print("-----------------")
print(result.model_dump_json(indent=4))
