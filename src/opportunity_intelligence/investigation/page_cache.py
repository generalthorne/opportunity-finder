
"""Persistent cache for investigated webpage content."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from opportunity_intelligence.url_utils import normalize_url

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_PAGE_CACHE_FILE = (
    PROJECT_ROOT / "data" / "processed" / "page_cache.json"
)


def calculate_page_hash(
    page_title: str | None,
    page_text: str,
) -> str:
    """Calculate a SHA-256 hash of webpage content."""
    content = f"{page_title or ''}\n{page_text}"

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


class PageCache:
    """Store and retrieve previously investigated webpages."""

    def __init__(self, cache_file: Path = DEFAULT_PAGE_CACHE_FILE):
        self.cache_file = Path(cache_file)
        self.entries = {}

        self.hits = 0
        self.misses = 0
        self.revalidated = 0
        self.downloads = 0

        self.load()

    def load(self) -> None:
        """Load cached webpage records."""
        if not self.cache_file.exists():
            self.entries = {}
            return

        try:
            with self.cache_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

            self.entries = data.get("entries", {})

            if not isinstance(self.entries, dict):
                raise ValueError("Page cache entries must be a dictionary.")

        except (json.JSONDecodeError, OSError, ValueError):
            logger.exception(
                "Could not load webpage cache from %s.",
                self.cache_file,
            )
            self.entries = {}

    def get(self, url: str) -> dict | None:
        """Retrieve a cached webpage record."""
        entry = self.entries.get(normalize_url(url))

        if not isinstance(entry, dict):
            self.misses += 1
            return None

        if not isinstance(entry.get("page_text"), str):
            self.misses += 1
            return None

        self.hits += 1
        return entry

    def get_conditional_headers(self, entry: dict) -> dict:
        """Build conditional HTTP request headers from cached metadata."""
        headers = {}

        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]

        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]

        return headers

    def set(
        self,
        url: str,
        page_title: str | None,
        page_text: str,
        status_code: int,
        headers: dict,
    ) -> None:
        """Store webpage content and its HTTP metadata."""
        normalized_url = normalize_url(url)

        normalized_headers = {
            key.lower(): value
            for key, value in headers.items()
        }

        now = datetime.now(timezone.utc).isoformat()

        self.entries[normalized_url] = {
            "page_title": page_title,
            "page_text": page_text,
            "content_hash": calculate_page_hash(
                page_title,
                page_text,
            ),
            "status_code": status_code,
            "etag": normalized_headers.get("etag"),
            "last_modified": normalized_headers.get("last-modified"),
            "fetched_at": now,
            "last_checked_at": now,
        }

    def mark_revalidated(self, url: str) -> None:
        """Record that the server confirmed cached content is unchanged."""
        entry = self.entries.get(normalize_url(url))

        if entry is not None:
            entry["last_checked_at"] = (
                datetime.now(timezone.utc).isoformat()
            )

    def save(self) -> None:
        """Persist webpage cache entries using an atomic file replacement."""
        self.cache_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_file = self.cache_file.with_suffix(
            self.cache_file.suffix + ".tmp"
        )

        try:
            with temporary_file.open("w", encoding="utf-8") as file:
                json.dump(
                    {"entries": self.entries},
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            temporary_file.replace(self.cache_file)

        except OSError:
            logger.exception(
                "Could not save webpage cache to %s.",
                self.cache_file,
            )
            raise
