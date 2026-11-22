
import pytest
from datetime import date
from pydantic import HttpUrl


from opportunity_intelligence.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityType,
    OpportunityStatus
)

from opportunity_intelligence.ranking.prioritizer import (
    load_ranking_config,
    score_category,
    score_quality,
    score_relevance,
    calculate_opportunity_score,
    rank_opportunities
)

from opportunity_intelligence.ranking.prioritizer import (
    load_ranking_config,
    score_category,
    score_quality,
    calculate_opportunity_score,
    rank_opportunities
)


@pytest.fixture
def ranking_config():
    return {
        "weights": {
            "relevance": 30,
            "eligibility": 25,
            "quality": 20,
            "deadline": 15,
            "category_preference": 10
        },
        "category_preferences": {
            "Research": 9,
            "Internship": 10,
            "Co-op": 10,
            "Fellowship": 9,
            "University Employment": 8,
            "Government": 8,
            "Other": 5
        }
    }


@pytest.fixture
def sample_opportunity():
    return Opportunity(
        title="Machine Learning Research Assistant",
        organization="University of Toronto",
        category=OpportunityCategory.RESEARCH,
        opportunity_type=OpportunityType.INDIVIDUAL,
        field=["Computer Science"],
        location="Toronto, Canada",
        work_mode="On-site",
        description="Assist with machine learning research.",
        evidence=["The source describes a research assistant position."],
        requirements=["Programming experience"],
        preferred_skills=["Python"],
        compensation="Paid",
        duration="Summer",
        start_date=None,
        deadline=None,
        start_date_text="May 2027",
        deadline_text="February 2027",
        eligibility="Undergraduate students",
        application_url=HttpUrl("https://example.com/apply"),
        source_url=HttpUrl("https://example.com/source"),
        status=OpportunityStatus.OPEN
    )


def test_load_ranking_config_uses_default_file():
    config = load_ranking_config()

    assert sum(config["weights"].values()) == 100
    assert "Research" in config["category_preferences"]


def test_load_ranking_config_rejects_invalid_weights(tmp_path):
    config_file = tmp_path / "ranking.yaml"

    config_file.write_text(
        """
weights:
  relevance: 30
  eligibility: 25
  quality: 20
  deadline: 15
  category_preference: 15

category_preferences:
  Research: 9
""",
        encoding="utf-8"
    )

    with pytest.raises(ValueError):
        load_ranking_config(config_file)


def test_score_category_uses_configured_preference(
    sample_opportunity,
    ranking_config
):
    assert score_category(sample_opportunity, ranking_config) == 90


def test_score_quality_returns_100_for_complete_opportunity(
    sample_opportunity
):
    assert score_quality(sample_opportunity) == 100


def test_score_quality_returns_zero_for_empty_information():
    opportunity = Opportunity(
        title="Unknown Opportunity",
        organization="Unknown Organization",
        category=OpportunityCategory.OTHER,
        source_url=HttpUrl("https://example.com")
    )

    assert score_quality(opportunity) == 0


def test_calculate_opportunity_score_returns_components(
    sample_opportunity,
    ranking_config
):
    result = calculate_opportunity_score(
        sample_opportunity,
        ranking_config
    )

    assert "overall_score" in result
    assert "component_scores" in result
    assert result["component_scores"]["category_preference"] == 90
    assert result["component_scores"]["quality"] == 100


def test_rank_opportunities_sorts_highest_first(
    sample_opportunity,
    ranking_config
):
    second_opportunity = sample_opportunity.model_copy(
        update={
            "title": "Incomplete Research Opportunity",
            "description": None,
            "location": None,
            "eligibility": None,
            "requirements": [],
            "deadline": None,
            "deadline_text": None,
            "application_url": None,
            "evidence": []
        }
    )

    ranked = rank_opportunities(
        [second_opportunity, sample_opportunity],
        ranking_config
    )

    assert ranked[0]["opportunity"].title == (
        "Machine Learning Research Assistant"
    )
    assert ranked[0]["overall_score"] > ranked[1]["overall_score"]


def test_score_relevance_matches_configured_keywords(
    sample_opportunity,
    ranking_config
):
    ranking_config["relevance_keywords"] = {
        "machine learning": 5,
        "computer science": 5,
        "statistics": 4,
        "finance": 3
    }

    score = score_relevance(sample_opportunity, ranking_config)

    assert score == 58.82


def test_score_relevance_returns_zero_without_matches(
    sample_opportunity,
    ranking_config
):
    ranking_config["relevance_keywords"] = {
        "quantum physics": 5,
        "biology": 3
    }

    assert score_relevance(sample_opportunity, ranking_config) == 0


def test_score_relevance_is_case_insensitive(
    sample_opportunity,
    ranking_config
):
    ranking_config["relevance_keywords"] = {
        "MACHINE LEARNING": 5
    }

    assert score_relevance(sample_opportunity, ranking_config) == 100