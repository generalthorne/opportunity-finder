
"""Load curated and approved discovered opportunity sources."""

from pathlib import Path
from urllib.parse import urldefrag, urlsplit, urlunsplit

import yaml
from pydantic import BaseModel, Field, HttpUrl


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "sources.yaml"
DEFAULT_DISCOVERED_CONFIG = (
    PROJECT_ROOT / "config" / "discovered_sources.yaml"
)


class Source(BaseModel):
    """Represent a website that can be investigated for opportunities."""

    id: str
    name: str
    url: HttpUrl
    region: str
    source_type: str
    categories: list[str] = Field(default_factory=list)
    enabled: bool = True
    notes: str | None = None


def normalize_url(url: str) -> str:
    """Normalize URLs for duplicate detection."""

    parts = urlsplit(urldefrag(url).url.strip())

    return urlunsplit((
        parts.scheme.lower(),
        parts.netloc.lower(),
        parts.path.rstrip("/"),
        parts.query,
        ""
    ))


def read_source_file(config_path: Path) -> list[Source]:
    """Read and validate sources from one YAML file."""

    if not config_path.exists():
        return []

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(
        data.get("sources"), list
    ):
        raise ValueError(
            f"Invalid source configuration: {config_path}"
        )

    return [
        Source.model_validate(source)
        for source in data["sources"]
    ]


def load_sources(
    config_path: Path = DEFAULT_CONFIG,
    discovered_config_path: Path | None = None
) -> list[Source]:
    """Load curated sources and approved discovered sources."""

    sources = read_source_file(config_path)

    if discovered_config_path is None and config_path == DEFAULT_CONFIG:
        discovered_config_path = DEFAULT_DISCOVERED_CONFIG

    if discovered_config_path is not None:
        sources.extend(read_source_file(discovered_config_path))

    seen_ids = set()
    seen_urls = set()

    for source in sources:
        normalized_url = normalize_url(str(source.url))

        if source.id in seen_ids:
            raise ValueError(
                f"Duplicate source ID found: {source.id}"
            )

        if normalized_url in seen_urls:
            raise ValueError(
                f"Duplicate source URL found: {normalized_url}"
            )

        seen_ids.add(source.id)
        seen_urls.add(normalized_url)

    return sources


def get_enabled_sources(sources: list[Source]) -> list[Source]:
    """Return only sources that are enabled."""

    return [
        source
        for source in sources
        if source.enabled
    ]
