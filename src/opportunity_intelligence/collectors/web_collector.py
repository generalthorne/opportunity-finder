
"""Retrieve webpages and report their HTTP response metadata."""

from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup


@dataclass
class FetchResult:
    """Represent the result of retrieving a webpage."""

    soup: BeautifulSoup | None
    status_code: int | None
    error: str | None
    headers: dict = field(default_factory=dict)
    not_modified: bool = False


def fetch_page(
    url: str,
    conditional_headers: dict | None = None,
) -> FetchResult:
    """Retrieve a webpage, optionally using conditional HTTP headers."""

    headers = {
        "User-Agent": "OpportunityIntelligence/1.0"
    }

    if conditional_headers:
        headers.update(conditional_headers)

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15,
        )

        response_headers = dict(
            getattr(response, "headers", {}) or {}
        )

        if response.status_code == 304:
            return FetchResult(
                soup=None,
                status_code=304,
                error=None,
                headers=response_headers,
                not_modified=True,
            )

        response.raise_for_status()

        return FetchResult(
            soup=BeautifulSoup(response.text, "html.parser"),
            status_code=response.status_code,
            error=None,
            headers=response_headers,
        )

    except requests.RequestException as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        response_headers = (
            dict(getattr(error.response, "headers", {}) or {})
            if error.response is not None
            else {}
        )

        return FetchResult(
            soup=None,
            status_code=status_code,
            error=str(error),
            headers=response_headers,
        )
