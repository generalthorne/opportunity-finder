
from datetime import datetime, timedelta, timezone

import pytest

from opportunity_intelligence.discovery.external_discovery import (
    load_search_history,
    save_search_history,
    select_queries_to_run,
)


@pytest.fixture
def sample_queries():
    return [
        {
            "id": "query_3",
            "query": "International research programs",
            "region": "International",
            "category": "research",
            "priority": 3,
        },
        {
            "id": "query_1",
            "query": "Canadian research programs",
            "region": "Canada",
            "category": "research",
            "priority": 1,
        },
        {
            "id": "query_2",
            "query": "US internships",
            "region": "US",
            "category": "internship",
            "priority": 2,
        },
    ]


def test_select_queries_prioritizes_lower_priority_number(sample_queries):
    selected = select_queries_to_run(
        queries=sample_queries,
        history={"queries": {}},
        max_searches=2,
    )

    assert [query["id"] for query in selected] == [
        "query_1",
        "query_2",
    ]


def test_select_queries_respects_search_limit(sample_queries):
    selected = select_queries_to_run(
        queries=sample_queries,
        history={"queries": {}},
        max_searches=1,
    )

    assert len(selected) == 1


def test_recently_attempted_queries_are_skipped(sample_queries):
    now = datetime.now(timezone.utc)

    history = {
        "queries": {
            "query_1": {
                "last_attempted_at": now.isoformat(),
            }
        }
    }

    selected = select_queries_to_run(
        queries=sample_queries,
        history=history,
        max_searches=3,
        cooldown_days=30,
        now=now,
    )

    assert "query_1" not in [
        query["id"] for query in selected
    ]


def test_old_queries_can_run_again(sample_queries):
    now = datetime.now(timezone.utc)
    old_attempt = now - timedelta(days=31)

    history = {
        "queries": {
            "query_1": {
                "last_attempted_at": old_attempt.isoformat(),
            }
        }
    }

    selected = select_queries_to_run(
        queries=sample_queries,
        history=history,
        max_searches=3,
        cooldown_days=30,
        now=now,
    )

    assert "query_1" in [
        query["id"] for query in selected
    ]


def test_force_ignores_cooldown(sample_queries):
    now = datetime.now(timezone.utc)

    history = {
        "queries": {
            query["id"]: {
                "last_attempted_at": now.isoformat(),
            }
            for query in sample_queries
        }
    }

    selected = select_queries_to_run(
        queries=sample_queries,
        history=history,
        max_searches=3,
        cooldown_days=30,
        force=True,
        now=now,
    )

    assert len(selected) == 3


def test_history_can_be_saved_and_loaded(tmp_path):
    history_file = tmp_path / "search_history.json"

    history = {
        "queries": {
            "query_1": {
                "status": "success",
                "candidate_count": 4,
            }
        }
    }

    save_search_history(history, history_file)
    loaded = load_search_history(history_file)

    assert loaded == history


def test_invalid_search_limit_is_rejected(sample_queries):
    with pytest.raises(ValueError):
        select_queries_to_run(
            queries=sample_queries,
            history={"queries": {}},
            max_searches=0,
        )


def test_negative_cooldown_is_rejected(sample_queries):
    with pytest.raises(ValueError):
        select_queries_to_run(
            queries=sample_queries,
            history={"queries": {}},
            cooldown_days=-1,
        )
