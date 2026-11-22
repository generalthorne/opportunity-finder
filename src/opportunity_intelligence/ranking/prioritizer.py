
"""Rank opportunities using configurable scoring criteria."""

from pathlib import Path

import yaml

from datetime import date

from opportunity_intelligence.models import Opportunity

from opportunity_intelligence.eligibility.evaluator import (
    evaluate_eligibility,
    load_user_profile,
    EligibilityStatus
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "ranking.yaml"


def load_ranking_config(config_path: Path = DEFAULT_CONFIG) -> dict:
    """Load and validate the ranking configuration."""

    with config_path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Invalid ranking configuration.")

    weights = config.get("weights")
    preferences = config.get("category_preferences")

    required_weights = {
        "relevance",
        "eligibility",
        "quality",
        "deadline",
        "category_preference"
    }

    if not isinstance(weights, dict) or set(weights) != required_weights:
        raise ValueError("Ranking configuration has invalid weights.")

    if sum(weights.values()) != 100:
        raise ValueError("Ranking weights must add up to 100.")

    if not isinstance(preferences, dict) or not preferences:
        raise ValueError("Category preferences must be a non-empty dictionary.")

    for category, score in preferences.items():
        if not isinstance(category, str):
            raise ValueError("Category names must be strings.")

        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("Category preference scores must be numeric.")

        if not 0 <= score <= 10:
            raise ValueError("Category preference scores must be between 0 and 10.")

    return config



def score_category(
    opportunity: Opportunity,
    config: dict
) -> float:
    """Score an opportunity according to its configured category preference."""

    preferences = config["category_preferences"]
    category = opportunity.category.value

    preference_score = preferences.get(category, 5)

    return preference_score * 10


def score_relevance(
    opportunity: Opportunity,
    config: dict
) -> float:
    """Score how closely an opportunity matches configured interests."""

    keywords = config.get("relevance_keywords", {})

    searchable_text = " ".join([
        opportunity.title or "",
        opportunity.description or "",
        " ".join(opportunity.field),
        " ".join(opportunity.requirements),
        " ".join(opportunity.preferred_skills)
    ]).casefold()

    total_weight = sum(keywords.values())

    if total_weight == 0:
        return 0.0

    matched_weight = sum(
        weight
        for keyword, weight in keywords.items()
        if keyword.casefold() in searchable_text
    )

    return round(matched_weight / total_weight * 100, 2)


def score_deadline(opportunity: Opportunity) -> float:
    """Score an opportunity based on how much time remains before its deadline."""

    if opportunity.deadline is None:
        return 50.0

    days_remaining = (opportunity.deadline - date.today()).days

    if days_remaining < 0:
        return 0.0
    if days_remaining <= 7:
        return 100.0
    if days_remaining <= 30:
        return 85.0
    if days_remaining <= 60:
        return 70.0
    if days_remaining <= 90:
        return 55.0

    return 40.0


def score_quality(opportunity: Opportunity) -> float:
    """Score the completeness of an opportunity's extracted information."""

    fields = [
        opportunity.description,
        opportunity.location,
        opportunity.eligibility,
        opportunity.requirements,
        opportunity.deadline or opportunity.deadline_text,
        opportunity.application_url,
        opportunity.evidence
    ]

    completed_fields = sum(bool(field) for field in fields)

    return completed_fields / len(fields) * 100


def calculate_opportunity_score(
    opportunity: Opportunity,
    config: dict
) -> dict:
    """Calculate an initial score for an opportunity."""

    category_score = score_category(opportunity, config)
    quality_score = score_quality(opportunity)
    relevance_score = score_relevance(opportunity, config)
    profile = load_user_profile()
    eligibility_result = evaluate_eligibility(
        opportunity.eligibility,
        profile
    )

    eligibility_scores = {
        EligibilityStatus.ELIGIBLE: 100,
        EligibilityStatus.FUTURE_ELIGIBLE: 65,
        EligibilityStatus.UNCERTAIN: 50,
        EligibilityStatus.NOT_ELIGIBLE: 0
    }

    eligibility_score = eligibility_scores[eligibility_result["status"]]
    deadline_score = score_deadline(opportunity)

    weights = config["weights"]

    overall_score = (
        relevance_score * weights["relevance"]
        + eligibility_score * weights["eligibility"]
        + quality_score * weights["quality"]
        + deadline_score * weights["deadline"]
        + category_score * weights["category_preference"]
    ) / 100

    return {
        "overall_score": round(overall_score, 2),
        "component_scores": {
            "relevance": relevance_score,
            "eligibility": eligibility_score,
            "quality": round(quality_score, 2),
            "deadline": deadline_score,
            "category_preference": category_score
        },
        "eligibility": {
            "status": eligibility_result["status"].value,
            "reason": eligibility_result["reason"]
        }
    }


def rank_opportunities(
    opportunities: list[Opportunity],
    config: dict
) -> list[dict]:
    """Score and sort opportunities from highest to lowest."""

    ranked_opportunities = []

    for opportunity in opportunities:
        result = calculate_opportunity_score(opportunity, config)

        ranked_opportunities.append({
            "opportunity": opportunity,
            **result
        })

    return sorted(
        ranked_opportunities,
        key=lambda item: item["overall_score"],
        reverse=True
    )
