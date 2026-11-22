
"""Identify, classify, and rank links that may contain opportunities."""


KEYWORD_WEIGHTS = {
    "undergraduate research": 5,
    "research opportunities": 5,
    "summer research": 5,
    "student employment": 5,
    "student jobs": 5,
    "internship": 5,
    "co-op": 5,
    "coop": 5,
    "fellowship": 4,
    "early career": 4,
    "opportunit": 3,
    "employment": 3,
    "career": 3,
    "scholarship": 3,
    "research": 2,
    "position": 2,
    "job": 2,
    "funding": 2,
    "summer": 1,
    "student": 1,
    "apply": 1
}


DIRECTORY_KEYWORDS = [
    "advertised projects",
    "funding search",
    "all opportunities",
    "research experiences for undergraduates",
    "research opportunity directory",
    "opportunity directory"
]


INFORMATIONAL_KEYWORDS = [
    "how to apply",
    "applying to",
    "application process",
    "research preparation",
    "frequently asked questions",
    "eligibility requirements"
]


IRRELEVANT_KEYWORDS = [
    "skip to content",
    "skip to main content",
    "contact us",
    "about us",
    "privacy policy",
    "accessibility",
    "staff opportunities",
    "faculty opportunities",
    "librarian opportunities",
    "emergency posting"
]


def classify_link(link: dict) -> str:
    """Classify a link by the kind of page it likely represents."""

    text = link.get("text", "").lower()
    url = link.get("url", "").lower()

    searchable_text = f"{text} {url}"

    # Empty links and common navigation links are not useful candidates.
    if not text.strip():
        return "irrelevant"

    if any(keyword in searchable_text for keyword in IRRELEVANT_KEYWORDS):
        return "irrelevant"

    if any(keyword in searchable_text for keyword in DIRECTORY_KEYWORDS):
        return "directory"

    if any(keyword in searchable_text for keyword in INFORMATIONAL_KEYWORDS):
        return "informational"

    # Specific research opportunity pages often use this URL structure.
    if "/research_opps/" in url:
        return "opportunity"

    # These terms are strong indicators of individual postings.
    opportunity_keywords = [
        "fellowship",
        "internship",
        "co-op",
        "coop",
        "summer research",
        "student position",
        "student job",
        "research funding",
        "research program",
        "research experience",
        "undergraduate research opportunity",
        "summer program",
        "student employment",
        "student recruitment",
        "student work placement",
        "research affiliate program",
        "research associate",
        "research assistant",
        "research scientist",
        "undergraduate program",
        "scholars program",
        "student opportunities",
        "summer associates",
        "actuarial intern",
        "research fellows",
        "research fellows program",
        "early career program",
        "student workforce",
    ]

    if any(keyword in searchable_text for keyword in opportunity_keywords):
        return "opportunity"

    # Broad opportunity pages are often directories.
    if any(keyword in searchable_text for keyword in [
        "research opportunities",
        "student opportunities",
        "early careers",
        "research experiences for undergraduates"
    ]):
        return "directory"

    return "other"


def score_link(link: dict) -> dict:
    """Return a link with its relevance score, keywords, and classification."""

    text = link.get("text", "").lower()
    url = link.get("url", "").lower()

    searchable_text = f"{text} {url}"

    matched_keywords = []
    score = 0

    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in searchable_text:
            matched_keywords.append(keyword)
            score += weight

    link_type = classify_link(link)

    # Irrelevant navigation links should never rank as useful candidates.
    if link_type == "irrelevant":
        score = 0

    return {
        **link,
        "relevance_score": score,
        "matched_keywords": matched_keywords,
        "link_type": link_type
    }


def filter_relevant_links(
    links: list[dict],
    min_score: int = 2
) -> list[dict]:
    """Return scored links that are worth investigating."""

    scored_links = [
        score_link(link)
        for link in links
    ]

    relevant_links = [
        link
        for link in scored_links
        if link["relevance_score"] >= min_score
        and link["link_type"] != "irrelevant"
    ]

    return sorted(
        relevant_links,
        key=lambda link: link["relevance_score"],
        reverse=True
    )
