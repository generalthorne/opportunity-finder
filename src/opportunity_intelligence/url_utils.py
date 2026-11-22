
"""Utilities for normalizing webpage URLs."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


TRACKING_PARAMETERS = {
    "fbclid",
    "gclid",
    "dclid",
    "msclkid",
    "mc_cid",
    "mc_eid",
}


def normalize_url(url: str) -> str:
    """Normalize a URL while preserving parameters that may affect content."""
    parsed = urlsplit(url.strip())

    query_parameters = [
        (key, value)
        for key, value in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
        if (
            not key.lower().startswith("utm_")
            and key.lower() not in TRACKING_PARAMETERS
        )
    ]

    return urlunsplit((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        urlencode(query_parameters),
        "",
    ))
