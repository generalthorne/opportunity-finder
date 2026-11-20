from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class FetchResult:
    """Represent the result of retrieving a webpage."""

    soup: BeautifulSoup | None
    status_code: int | None
    error: str | None


def fetch_page(url: str) -> FetchResult:
    """Retrieve a webpage and report the result."""

    headers = {
        "User-Agent": "OpportunityIntelligence/1.0"
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        response.raise_for_status()

        return FetchResult(
            soup=BeautifulSoup(response.text, "html.parser"),
            status_code=response.status_code,
            error=None
        )

    except requests.RequestException as error:
        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        return FetchResult(
            soup=None,
            status_code=status_code,
            error=str(error)
        )