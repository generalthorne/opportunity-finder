
import requests
from bs4 import BeautifulSoup


def fetch_page(url: str) -> BeautifulSoup | None:
    """Retrieve a webpage and return its parsed HTML.

    Return None if the webpage cannot be retrieved.
    """

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

        return BeautifulSoup(response.text, "html.parser")

    except requests.RequestException as error:
        print(f"Could not retrieve {url}: {error}")
        return None
