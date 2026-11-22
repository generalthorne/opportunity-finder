
from opportunity_intelligence.discovery.source_registry import (
    load_sources,
    get_enabled_sources
)


def test_load_sources():
    sources = load_sources()

    assert len(sources) >= 6
    assert sources[0].id == "uoft_research"

    source_ids = [source.id for source in sources]

    # Every source should have a unique identifier.
    assert len(source_ids) == len(set(source_ids))


def test_get_enabled_sources():
    sources = load_sources()

    enabled_sources = get_enabled_sources(sources)

    assert len(enabled_sources) >= 6
    assert all(source.enabled for source in enabled_sources)

    # Disabled discovered sources must not enter the active registry.
    assert all(
        source.enabled
        for source in enabled_sources
    )


def test_source_has_valid_url():
    sources = load_sources()

    for source in sources:
        assert str(source.url).startswith("https://")


def test_discovered_source_is_loaded():
    sources = load_sources()

    source_ids = {source.id for source in sources}

    assert (
        "undergrad_engineering_utoronto_ca_experiential_learning_research_opportunities"
        in source_ids
    )
