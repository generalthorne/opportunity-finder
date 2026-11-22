
"""Persistent cache for webpage LLM extraction results."""

import hashlib
import json
import logging
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from opportunity_intelligence.extraction.extraction_result import (
    PageExtractionResult,
)

from opportunity_intelligence.url_utils import normalize_url

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CACHE_FILE = (
    PROJECT_ROOT / "data" / "processed" / "extraction_cache.json"
)


def normalize_cache_url(url: str) -> str:
    """Normalize a webpage URL for consistent cache lookup."""
    return normalize_url(url)

    


def calculate_content_hash(
    page_text: str,
    page_title: str | None = None,
) -> str:
    """Generate a SHA-256 hash from the page title and text."""
    content = f"{page_title or ''}\n{page_text}"

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


class ExtractionCache:
    """Load, retrieve, and persist structured LLM extraction results."""

    def __init__(self, cache_file: Path = DEFAULT_CACHE_FILE):
        self.cache_file = Path(cache_file)
        self.entries = {}

        self.hits = 0
        self.misses = 0

        self.load()

    def load(self) -> None:
        """Load cached results from disk."""
        if not self.cache_file.exists():
            self.entries = {}
            return

        try:
            with self.cache_file.open("r", encoding="utf-8") as file:
                data = json.load(file)

            self.entries = data.get("entries", {})

            if not isinstance(self.entries, dict):
                raise ValueError("Cache entries must be a dictionary.")

        except (json.JSONDecodeError, OSError, ValueError):
            logger.exception(
                "Could not load extraction cache from %s.",
                self.cache_file
            )
            self.entries = {}

    def get(
        self,
        url: str,
        content_hash: str,
        model: str,
    ) -> PageExtractionResult | None:
        """Return a cached result if the page content and model match."""
        normalized_url = normalize_cache_url(url)
        entry = self.entries.get(normalized_url)

        if not isinstance(entry, dict):
            self.misses += 1
            return None

        if entry.get("content_hash") != content_hash:
            self.misses += 1
            return None

        if entry.get("model") != model:
            self.misses += 1
            return None

        try:
            result = PageExtractionResult.model_validate(
                entry["result"]
            )
        except (KeyError, ValueError):
            logger.warning(
                "Invalid cached extraction result for %s.",
                normalized_url
            )
            self.misses += 1
            return None

        self.hits += 1
        return result

    def set(
        self,
        url: str,
        content_hash: str,
        model: str,
        result: PageExtractionResult,
    ) -> None:
        """Store a structured extraction result in the cache."""
        normalized_url = normalize_cache_url(url)

        self.entries[normalized_url] = {
            "content_hash": content_hash,
            "model": model,
            "result": result.model_dump(mode="json"),
        }

    def save(self) -> None:
        """Persist all cached results to disk."""
        self.cache_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_file = self.cache_file.with_suffix(
            self.cache_file.suffix + ".tmp"
        )

        data = {
            "entries": self.entries
        }

        try:
            with temporary_file.open("w", encoding="utf-8") as file:
                json.dump(
                    data,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

            temporary_file.replace(self.cache_file)

        except OSError:
            logger.exception(
                "Could not save extraction cache to %s.",
                self.cache_file
            )
            raise
