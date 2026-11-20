import json

with open(
    "data/raw/investigated_pages.json",
    "r",
    encoding="utf-8"
) as file:
    data = json.load(file)

target_urls = [
    "professional-experience-year-pey/",
    "experiential-learning/"
]

for page in data["pages"]:
    url = page.get("url", "")

    if any(target in url for target in target_urls):
        text = page.get("page_text") or ""

        print("=" * 100)
        print("URL:", url)
        print("TITLE:", page.get("page_title"))
        print("TEXT LENGTH:", len(text))
        print("LAST 2000 CHARACTERS:")
        print(text[-2000:])
        print()