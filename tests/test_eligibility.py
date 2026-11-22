
from opportunity_intelligence.eligibility.evaluator import (
    EligibilityStatus,
    evaluate_eligibility,
    load_user_profile
)


def sample_profile():
    return {
        "education": {
            "level": "undergraduate",
            "institution": "University of Toronto",
            "year_of_study": 1,
            "program": ["Computer Science"]
        },
        "location": {
            "country": "Canada"
        }
    }


def test_missing_requirements_are_uncertain():
    result = evaluate_eligibility(None, sample_profile())

    assert result["status"] == EligibilityStatus.UNCERTAIN


def test_missing_profile_is_uncertain():
    result = evaluate_eligibility(
        "Open to undergraduate students.",
        {}
    )

    assert result["status"] == EligibilityStatus.UNCERTAIN


def test_undergraduate_is_not_eligible_for_graduate_only_position():
    result = evaluate_eligibility(
        "Graduate students only.",
        sample_profile()
    )

    assert result["status"] == EligibilityStatus.NOT_ELIGIBLE


def test_first_year_is_future_eligible_for_third_year_requirement():
    result = evaluate_eligibility(
        "Applicants must be at least third year undergraduate students.",
        sample_profile()
    )

    assert result["status"] == EligibilityStatus.FUTURE_ELIGIBLE


def test_unconfirmed_citizenship_is_uncertain():
    result = evaluate_eligibility(
        "Canadian citizens only.",
        sample_profile()
    )

    assert result["status"] == EligibilityStatus.UNCERTAIN


def test_unrecognized_requirements_are_uncertain():
    result = evaluate_eligibility(
        "Applicants must demonstrate strong programming skills.",
        sample_profile()
    )

    assert result["status"] == EligibilityStatus.UNCERTAIN


def test_load_user_profile_uses_default_file():
    profile = load_user_profile()

    assert profile["education"]["institution"] == "University of Toronto"
    assert profile["education"]["year_of_study"] == 1
