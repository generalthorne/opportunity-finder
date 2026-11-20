import json
from pathlib import Path

file_path = Path("data/raw/investigated_pages.json")

with file_path.open("r", encoding="utf-8") as file:
    data = json.load(file)

failed_pages = [
    page
    for page in data["pages"]
    if page["status"] == "failed"
]

print(f"Failed pages: {len(failed_pages)}")
print("-" * 100)

for page in failed_pages:
    print(f"Link text: {page.get('text')}")
    print(f"URL: {page['url']}")
    print()