
"""Discover and rank candidate opportunity sources."""

import json
import re

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urldefrag, urlsplit, urlunsplit

from opportunity_intelligence.discovery.source_registry import (
    load_sources
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_FILE = PROJECT_ROOT / "data" / "processed" / "prioritized_links.json"
OUTPUT_FILE = PROJECT_ROOT / "data" / "processed" / "source_candidates.json"


SOURCE_KEYWORDS = {
    "directory": [
        "directory",
        "database",
        "opportunity search",
        "search the directory",
        "research experiences for undergraduates",
        "undergraduate research explorer",
        "funding opportunities",
        "funding search",
        "all opportunities",
        "opportunity listings"
    ],
    "portal": [
        "career portal",
        "student employment",
        "student jobs",
        "job board",
        "career opportunities",
        "early careers",
        "internship opportunities",
        "student opportunities"
    ],
    "program": [
        "research programs",
        "summer programs",
        "fellowship programs",
        "research-opportunities"
    ]
}

INFORMATIONAL_SOURCE_EXCLUSIONS = [
    "shaping",
    "equitable",
    "inclusive",
    "considerations",
    "value of",
    "other ways to support",
    "support students",
    "recruiting",
    "working with",
    "faculty-staff",
    "faculty staff",
    "how to apply",
    "application process",
    "research preparation",
    "eligibility requirements",
    "frequently asked questions",
    "how to",
    "what are",
    "what is",
    "guide to",
    "beginner's guide",
    "tips for",
    "explained",
    "understanding",
    "advice on",
    "blog"
]


CATEGORY_KEYWORDS = {
    "research": ["research", "reu", "urop"],
    "internship": ["internship", "intern"],
    "coop": ["co-op", "coop"],
    "fellowship": ["fellowship"],
    "university_employment": [
        "student employment",
        "student jobs",
        "work study"
    ],
    "government": ["government", "federal"]
}

INDIVIDUAL_OPPORTUNITY_TERMS = [
    "apply now",
    "job posting",
    "position available",
    "research assistant position",
    "internship position",
    "application deadline"
]


def normalize_url(url: str) -> str:
    """Normalize URLs for source deduplication."""

    url = urldefrag(url).url.strip()
    parts = urlsplit(url)

    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    path = parts.path.rstrip("/")

    return urlunsplit((
        scheme,
        netloc,
        path,
        parts.query,
        ""
    ))


def make_source_id(url: str) -> str:
    """Generate a stable source ID from a URL."""

    parts = urlsplit(url)

    text = f"{parts.netloc} {parts.path}"
    text = text.lower()

    identifier = re.sub(
        r"[^a-z0-9]+",
        "_",
        text
    ).strip("_")

    return identifier[:80] or "discovered_source"



def get_searchable_text(link: dict) -> str:
    """Combine title, text, snippet, and URL for classification."""

    return (
        f"{link.get('title', '')} "
        f"{link.get('text', '')} "
        f"{link.get('snippet', '')} "
        f"{link.get('url', '')}"
    ).casefold()




def identify_source_type(text: str) -> str | None:
    """Identify whether a page has recognizable source functionality."""

    for source_type, keywords in SOURCE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return source_type

    return None



def identify_categories(text: str) -> list[str]:
    """Infer opportunity categories from available evidence."""

    categories = []

    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            categories.append(category)

    return categories



def calculate_source_score(
    link: dict,
    source_type: str
) -> int:
    """Calculate a source suitability score from 0 to 100."""

    # A source must first have passed source-intent classification.
    score = 35

    # General link relevance contributes, but cannot dominate.
    relevance = link.get("relevance_score", 0)
    score += min(relevance * 2, 20)

    type_scores = {
        "directory": 20,
        "portal": 20,
        "program": 15
    }

    score += type_scores[source_type]

    categories = identify_categories(
        get_searchable_text(link)
    )

    score += min(len(categories) * 5, 15)

    if link.get("discovered_in"):
        score += 5

    if link.get("link_type") == "directory":
        score += 5

    return min(score, 100)




def is_source_candidate(link: dict) -> bool:
    """Determine whether a link represents a potentially reusable source."""

    if not link.get("url"):
        return False

    text = get_searchable_text(link)

    if any(
        keyword in text
        for keyword in INFORMATIONAL_SOURCE_EXCLUSIONS
    ):
        return False

    if link.get("link_type") in {
        "opportunity",
        "informational",
        "irrelevant"
    }:
        return False

    if any(
        term in text
        for term in INDIVIDUAL_OPPORTUNITY_TERMS
    ):
        return False

    # Require an identifiable directory, portal, or program signal.
    return identify_source_type(text) is not None



def get_region(link: dict) -> str:
    """Infer the region from the original discovery sources."""

    regions = []

    for source in link.get("discovered_in", []):
        region = source.get("region")

        if region and region not in regions:
            regions.append(region)

    if not regions:
        return "Unknown"

    return ", ".join(regions)


def build_candidate(link: dict) -> dict | None:
    """Convert a prioritized link into a source candidate."""

    if not is_source_candidate(link):
        return None

    url = normalize_url(link["url"])
    text = get_searchable_text(link)

    source_type = identify_source_type(text)

    if source_type is None:
        return None

    categories = identify_categories(text)

    if not categories:
        return None

    score = calculate_source_score(
        link,
        source_type
    )

    discovered_in = link.get("discovered_in", [])

    discovery_evidence = {
        "matched_keywords": link.get("matched_keywords", []),
        "relevance_score": link.get("relevance_score", 0),
        "original_link_type": link.get("link_type"),
        "discovered_in": discovered_in,
        "search_query": link.get("search_query"),
        "search_provider": link.get("search_provider"),
        "search_score": link.get("search_score"),
        "snippet": link.get("snippet")
    }

    return {
        "id": make_source_id(url),
        "name": link.get("title") or link.get("text", "").strip(),
        "url": url,
        "region": get_region(link),
        "source_type": source_type,
        "categories": categories,
        "enabled": False,
        "notes": "Automatically discovered source awaiting review.",
        "discovery_score": score,
        "discovery_evidence": discovery_evidence,
        "status": "pending"
    }


def get_existing_source_urls() -> set[str]:
    """Get normalized URLs already present in the source registry."""

    try:
        sources = load_sources()
    except FileNotFoundError:
        return set()

    return {
        normalize_url(str(source.url))
        for source in sources
    }


def discover_source_candidates(
    input_file: Path = INPUT_FILE,
    existing_urls: set[str] | None = None,
    min_score: int = 35
) -> list[dict]:
    """Discover, score, and deduplicate candidate sources."""

    if not input_file.exists():
        raise FileNotFoundError(
            f"Prioritized links file not found: {input_file}"
        )

    with input_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    links = data.get("links", [])

    if existing_urls is None:
        existing_urls = get_existing_source_urls()

    existing_urls = {
        normalize_url(url)
        for url in existing_urls
    }

    candidates = {}

    for link in links:
        candidate = build_candidate(link)

        if candidate is None:
            continue

        if candidate["discovery_score"] < min_score:
            continue

        normalized_url = normalize_url(candidate["url"])

        if normalized_url in existing_urls:
            continue

        if normalized_url in candidates:
            if (
                candidate["discovery_score"]
                > candidates[normalized_url]["discovery_score"]
            ):
                candidates[normalized_url] = candidate

            continue

        candidates[normalized_url] = candidate

    results = list(candidates.values())

    return sorted(
        results,
        key=lambda candidate: candidate["discovery_score"],
        reverse=True
    )


def save_source_candidates(
    candidates: list[dict],
    output_file: Path = OUTPUT_FILE
) -> None:
    """Persist discovered candidates for manual review."""

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    data = {
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "total_candidates": len(candidates),
        "candidates": candidates
    }

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def run_source_discovery(
    input_file: Path = INPUT_FILE,
    output_file: Path = OUTPUT_FILE,
    min_score: int = 35
) -> list[dict]:
    """Run the source discovery pipeline."""

    candidates = discover_source_candidates(
        input_file=input_file,
        min_score=min_score
    )

    save_source_candidates(
        candidates,
        output_file
    )

    print(f"Source candidates discovered: {len(candidates)}")
    print(f"Saved to: {output_file}")

    return candidates


if __name__ == "__main__":
    run_source_discovery()
