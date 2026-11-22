
"""Verify whether discovered webpages are useful opportunity sources."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup

from opportunity_intelligence.collectors.web_collector import (
    FetchResult,
    fetch_page,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Strong signals that a page is a reusable opportunity resource.
POSITIVE_SIGNALS = {
    "directory": [
        "opportunity directory",
        "research directory",
        "search opportunities",
        "browse opportunities",
        "opportunity database",
        "all opportunities",
        "research experiences for undergraduates",
        "undergraduate research opportunities",
        "internship listings",
        "job board",
    ],
    "portal": [
        "career portal",
        "student employment",
        "student jobs",
        "co-op opportunities",
        "internship opportunities",
        "early career opportunities",
        "student opportunities",
    ],
    "program": [
        "undergraduate research program",
        "summer research program",
        "summer research opportunities",
        "research internship",
        "undergraduate internship",
        "fellowship program",
        "research fellowship",
        "research assistant",
    ],
}

# These signals suggest that a page is informational rather than a source.
NEGATIVE_SIGNALS = [
    "how to",
    "what are some",
    "what is",
    "guide to",
    "beginner's guide",
    "tips for",
    "explained",
    "advice on",
    "frequently asked questions",
    "discussion forum",
    "community discussion",
]

NEGATIVE_URL_TERMS = [
    "/blog/",
    "/forum/",
    "/discussion/",
    "quora.com",
    "reddit.com",
]

GENERIC_POSITIVE_SIGNALS = [
    "application deadline",
    "eligibility requirements",
    "how to apply",
    "application information",
]


def extract_page_text(soup: BeautifulSoup) -> str:
    """Extract readable webpage text while removing non-content elements."""

    for element in soup([
        "script",
        "style",
        "noscript",
        "svg",
        "nav",
        "footer",
    ]):
        element.decompose()

    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def find_signals(text: str, signals: list[str]) -> list[str]:
    """Return signals found in normalized text."""

    normalized = text.casefold()
    return [
        signal
        for signal in signals
        if signal.casefold() in normalized
    ]


def classify_page(
    title: str,
    url: str,
    page_text: str,
) -> dict:
    """Classify a webpage using evidence from its title, URL, and content."""

    title_and_url = f"{title} {url}".casefold()
    searchable_text = f"{title} {url} {page_text}".casefold()

    positive_signals = []
    for source_type, signals in POSITIVE_SIGNALS.items():
        for signal in find_signals(searchable_text, signals):
            positive_signals.append({
                "type": source_type,
                "signal": signal,
            })

    generic_signals = find_signals(
        searchable_text,
        GENERIC_POSITIVE_SIGNALS,
    )

    negative_signals = find_signals(
        title_and_url,
        NEGATIVE_SIGNALS,
    )

    negative_signals.extend(
        term for term in NEGATIVE_URL_TERMS
        if term in title_and_url
    )

    # Generic application language is weaker evidence than an actual
    # directory, portal, or named opportunity program.
    positive_score = len(positive_signals) * 2
    positive_score += len(generic_signals)

    negative_score = len(negative_signals) * 3

    score = max(0, min(100, 50 + positive_score * 5 - negative_score * 5))

    if negative_signals:
        classification = "not_source"
    elif positive_score >= 4 and positive_score > negative_score:
        classification = "verified_source_candidate"
    else:
        classification = "needs_review"

    source_types = list(dict.fromkeys(
        item["type"] for item in positive_signals
    ))

    return {
        "classification": classification,
        "score": score,
        "source_types": source_types,
        "positive_signals": positive_signals,
        "generic_positive_signals": generic_signals,
        "negative_signals": negative_signals,
    }


def verify_candidate(
    candidate: dict,
    fetcher: Callable[[str], FetchResult] = fetch_page,
) -> dict:
    """Fetch and assess one discovered source candidate."""

    result = fetcher(candidate["url"])
    verified_at = datetime.now(timezone.utc).isoformat()

    if result.soup is None:
        page_status = (
            "inaccessible"
            if result.status_code in {401, 403, 404, 410, 429}
            else "failed"
        )

        candidate["page_verification"] = {
            "status": page_status,
            "classification": "needs_review",
            "http_status": result.status_code,
            "error": result.error,
            "verified_at": verified_at,
        }
        return candidate

    page_title = (
        result.soup.title.get_text(" ", strip=True)
        if result.soup.title
        else ""
    )

    page_text = extract_page_text(result.soup)

    assessment = classify_page(
        title=page_title,
        url=candidate["url"],
        page_text=page_text,
    )

    candidate["page_verification"] = {
        "status": "completed",
        "http_status": result.status_code,
        "page_title": page_title,
        "page_text_excerpt": page_text[:1000],
        "verified_at": verified_at,
        **assessment,
    }

    return candidate


def verify_candidates(
    candidates: list[dict],
    fetcher: Callable[[str], FetchResult] = fetch_page,
    delay_seconds: float = 1.0,
) -> list[dict]:
    """Verify multiple candidates without changing their approval status."""

    import time

    verified = []

    for index, candidate in enumerate(candidates):
        verified.append(
            verify_candidate(candidate, fetcher=fetcher)
        )

        if delay_seconds > 0 and index < len(candidates) - 1:
            time.sleep(delay_seconds)

    return verified
