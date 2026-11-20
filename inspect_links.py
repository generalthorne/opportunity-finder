
import json
from pathlib import Path

from opportunity_intelligence.discovery.link_filter import (
    filter_relevant_links
)


raw_data_dir = Path("data/raw")

files = list(raw_data_dir.glob("*.json"))

for file_path in files:
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    links = data.get("links", [])
    relevant_links = filter_relevant_links(links)

    print(f"\n{file_path.name}")
    print("-" * 100)

    for link in relevant_links[:10]:
        score = link["relevance_score"]
        text = link["text"][:65]
        url = link["url"]

        link_type = link["link_type"]
        print(f"{score:>2} | {link_type:<13} | {text} | {url}")
