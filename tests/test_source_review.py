
import json

import pytest
import yaml

from opportunity_intelligence.discovery import source_review


@pytest.fixture
def review_files(tmp_path, monkeypatch):
    """Create isolated registry and candidate files for testing."""

    curated_file = tmp_path / "sources.yaml"
    discovered_file = tmp_path / "discovered_sources.yaml"
    candidates_file = tmp_path / "source_candidates.json"

    curated_file.write_text(
        yaml.safe_dump({
            "sources": [{
                "id": "existing_source",
                "name": "Existing Source",
                "url": "https://existing.example.com",
                "region": "Canada",
                "source_type": "directory",
                "categories": ["research"],
                "enabled": True
            }]
        }),
        encoding="utf-8"
    )

    candidate_data = {
        "discovered_at": "2026-11-21T00:00:00+00:00",
        "total_candidates": 2,
        "candidates": [
            {
                "id": "new_research_source",
                "name": "New Research Source",
                "url": "https://new.example.com/research",
                "region": "Canada",
                "source_type": "directory",
                "categories": ["research"],
                "enabled": False,
                "notes": "Awaiting review.",
                "discovery_score": 80,
                "discovery_evidence": {
                    "matched_keywords": ["research"]
                },
                "status": "pending"
            },
            {
                "id": "another_source",
                "name": "Another Source",
                "url": "https://another.example.com",
                "region": "United States",
                "source_type": "portal",
                "categories": ["internship"],
                "enabled": False,
                "notes": "Awaiting review.",
                "discovery_score": 70,
                "discovery_evidence": {},
                "status": "pending"
            }
        ]
    }

    candidates_file.write_text(
        json.dumps(candidate_data, indent=4),
        encoding="utf-8"
    )

    monkeypatch.setattr(
        source_review,
        "DEFAULT_CONFIG",
        curated_file
    )

    return curated_file, discovered_file, candidates_file


def test_list_pending_candidates(review_files):
    _, _, candidates_file = review_files

    candidates = source_review.list_pending_candidates(
        candidates_file
    )

    assert len(candidates) == 2


def test_approve_candidate_adds_source_to_registry(review_files):
    curated_file, discovered_file, candidates_file = review_files

    source = source_review.approve_source_candidate(
        "new_research_source",
        candidates_file,
        discovered_file
    )

    assert source.enabled is True

    registry = source_review.load_candidate_data(
        candidates_file
    )

    candidate = registry["candidates"][0]

    assert candidate["status"] == "approved"
    assert candidate["enabled"] is True
    assert candidate["reviewed_at"] is not None

    sources = yaml.safe_load(
        discovered_file.read_text(encoding="utf-8")
    )["sources"]

    assert len(sources) == 1
    assert sources[0]["id"] == "new_research_source"


def test_approved_source_is_loaded_with_curated_sources(review_files):
    curated_file, discovered_file, candidates_file = review_files

    source_review.approve_source_candidate(
        "new_research_source",
        candidates_file,
        discovered_file
    )

    from opportunity_intelligence.discovery.source_registry import (
        load_sources
    )

    sources = load_sources(
        curated_file,
        discovered_file
    )

    assert len(sources) == 2
    assert {
        source.id for source in sources
    } == {
        "existing_source",
        "new_research_source"
    }


def test_reject_candidate_preserves_reason(review_files):
    _, _, candidates_file = review_files

    source_review.reject_source_candidate(
        "new_research_source",
        "Page does not contain reusable opportunities.",
        candidates_file
    )

    data = source_review.load_candidate_data(
        candidates_file
    )

    candidate = data["candidates"][0]

    assert candidate["status"] == "rejected"
    assert candidate["enabled"] is False
    assert candidate["review_notes"] == (
        "Page does not contain reusable opportunities."
    )


def test_cannot_approve_candidate_twice(review_files):
    _, discovered_file, candidates_file = review_files

    source_review.approve_source_candidate(
        "new_research_source",
        candidates_file,
        discovered_file
    )

    with pytest.raises(ValueError, match="not pending"):
        source_review.approve_source_candidate(
            "new_research_source",
            candidates_file,
            discovered_file
        )


def test_rejection_requires_reason(review_files):
    _, _, candidates_file = review_files

    with pytest.raises(ValueError, match="reason is required"):
        source_review.reject_source_candidate(
            "new_research_source",
            "   ",
            candidates_file
        )


def test_duplicate_source_url_is_rejected(review_files):
    _, discovered_file, candidates_file = review_files

    data = source_review.load_candidate_data(candidates_file)
    data["candidates"][0]["url"] = (
        "https://existing.example.com/"
    )
    source_review.save_candidate_data(data, candidates_file)

    with pytest.raises(ValueError, match="URL already registered"):
        source_review.approve_source_candidate(
            "new_research_source",
            candidates_file,
            discovered_file
        )
