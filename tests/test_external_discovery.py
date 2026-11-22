
from pathlib import Path

import yaml

from opportunity_intelligence.discovery.external_discovery import (
    register_verified_sources,
)


def make_candidate(
    source_id="test-source",
    url="https://example.com/research",
    classification="verified_source_candidate",
    status="completed",
    score=85,
):
    return {
        "id": source_id,
        "name": "Example Research Opportunities",
        "url": url,
        "region": "Canada",
        "source_type": "directory",
        "categories": ["Research"],
        "enabled": False,
        "notes": "Discovered through external search.",
        "page_verification": {
            "status": status,
            "classification": classification,
            "score": score,
        },
    }


def test_registers_verified_source(tmp_path):
    registry = tmp_path / "discovered_sources.yaml"

    registered = register_verified_sources(
        [make_candidate()],
        discovered_config_path=registry,
    )

    assert len(registered) == 1
    assert registered[0].enabled is True

    data = yaml.safe_load(registry.read_text(encoding="utf-8"))

    assert len(data["sources"]) == 1
    assert data["sources"][0]["id"] == "test-source"
    assert data["sources"][0]["enabled"] is True


def test_does_not_register_unverified_source(tmp_path):
    registry = tmp_path / "discovered_sources.yaml"

    candidates = [
        make_candidate(
            classification="needs_review",
        ),
        make_candidate(
            source_id="rejected-source",
            url="https://example.com/blog",
            classification="not_source",
        ),
        make_candidate(
            source_id="inaccessible-source",
            url="https://example.com/private",
            status="inaccessible",
        ),
    ]

    registered = register_verified_sources(
        candidates,
        discovered_config_path=registry,
    )

    assert registered == []
    assert not registry.exists()


def test_does_not_register_low_confidence_source(tmp_path):
    registry = tmp_path / "discovered_sources.yaml"

    registered = register_verified_sources(
        [make_candidate(score=60)],
        discovered_config_path=registry,
    )

    assert registered == []
    assert not registry.exists()


def test_does_not_register_duplicate_url(tmp_path):
    registry = tmp_path / "discovered_sources.yaml"

    first = make_candidate()

    register_verified_sources(
        [first],
        discovered_config_path=registry,
    )

    duplicate = make_candidate(
        source_id="different-id",
        url="https://EXAMPLE.com/research/",
    )

    registered = register_verified_sources(
        [duplicate],
        discovered_config_path=registry,
    )

    assert registered == []

    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert len(data["sources"]) == 1


def test_does_not_register_duplicate_id(tmp_path):
    registry = tmp_path / "discovered_sources.yaml"

    register_verified_sources(
        [make_candidate()],
        discovered_config_path=registry,
    )

    duplicate = make_candidate(
        url="https://another-example.com/research",
    )

    registered = register_verified_sources(
        [duplicate],
        discovered_config_path=registry,
    )

    assert registered == []

    data = yaml.safe_load(registry.read_text(encoding="utf-8"))
    assert len(data["sources"]) == 1
