
from opportunity_intelligence.discovery.source_registry import (
    load_sources,
    get_enabled_sources
)


def test_load_sources():
    sources = load_sources()

    assert len(sources) == 6
    assert sources[0].id == "uoft_research"


def test_get_enabled_sources():
    sources = load_sources()

    enabled_sources = get_enabled_sources(sources)

    assert len(enabled_sources) == 6
    assert all(source.enabled for source in enabled_sources)


def test_source_has_valid_url():
    sources = load_sources()

    for source in sources:
        assert str(source.url).startswith("https://")
