
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, HttpUrl


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "sources.yaml"


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


def load_sources(config_path: Path = DEFAULT_CONFIG) -> list[Source]:
    """Load and validate opportunity sources from a YAML file."""

    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict) or not isinstance(data.get("sources"), list):
        raise ValueError("Invalid source configuration.")

    return [
        Source.model_validate(source)
        for source in data["sources"]
    ]


def get_enabled_sources(sources: list[Source]) -> list[Source]:
    """Return only sources that are enabled."""

    return [source for source in sources if source.enabled]
