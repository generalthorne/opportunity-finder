
"""Evaluate opportunity eligibility using a user profile."""

import re
from enum import Enum
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROFILE = PROJECT_ROOT / "config" / "user_profile.yaml"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "Eligible"
    NOT_ELIGIBLE = "Not eligible"
    FUTURE_ELIGIBLE = "Future eligible"
    UNCERTAIN = "Uncertain"


def load_user_profile(profile_path: Path = DEFAULT_PROFILE) -> dict:
    """Load the user's eligibility profile."""

    with profile_path.open("r", encoding="utf-8") as file:
        profile = yaml.safe_load(file)

    if not isinstance(profile, dict):
        raise ValueError("Invalid user profile.")

    return profile


def evaluate_eligibility(
    opportunity_eligibility: str | None,
    user_profile: dict
) -> dict:
    """Classify eligibility using known profile details and requirements."""

    if not opportunity_eligibility:
        return {
            "status": EligibilityStatus.UNCERTAIN,
            "reason": "Eligibility requirements were not provided."
        }

    if not user_profile:
        return {
            "status": EligibilityStatus.UNCERTAIN,
            "reason": "User profile is missing."
        }

    requirements = opportunity_eligibility.casefold()

    education = user_profile.get("education", {})
    current_year = education.get("year_of_study")
    current_level = education.get("level", "").casefold()

    # Check whether the opportunity is restricted to graduate students.
    graduate_only = any(
        phrase in requirements
        for phrase in [
            "graduate students only",
            "master's students only",
            "doctoral students only",
            "phd students only"
        ]
    )

    if graduate_only and current_level == "undergraduate":
        return {
            "status": EligibilityStatus.NOT_ELIGIBLE,
            "reason": "The opportunity is restricted to graduate students."
        }

    # Check minimum undergraduate year requirements.
    year_match = re.search(
        r"(?:at least|minimum of|minimum|entering)\s+"
        r"(first|second|third|fourth|1st|2nd|3rd|4th|\d)"
        r"(?:st|nd|rd|th)?\s+year",
        requirements
    )

    if year_match and isinstance(current_year, int):
        year_words = {
            "first": 1,
            "second": 2,
            "third": 3,
            "fourth": 4,
            "1st": 1,
            "2nd": 2,
            "3rd": 3,
            "4th": 4
        }

        required_year_text = year_match.group(1)
        required_year = year_words.get(
            required_year_text,
            int(required_year_text) if required_year_text.isdigit() else None
        )

        if required_year and current_year < required_year:
            return {
                "status": EligibilityStatus.FUTURE_ELIGIBLE,
                "reason": (
                    f"The opportunity requires at least year "
                    f"{required_year}; the profile indicates year "
                    f"{current_year}."
                )
            }

    # Citizenship and work authorization must not be guessed.
    restricted_status_terms = [
        "canadian citizens only",
        "u.s. citizens only",
        "us citizens only",
        "permanent residents only",
        "citizens or permanent residents"
    ]

    if any(term in requirements for term in restricted_status_terms):
        return {
            "status": EligibilityStatus.UNCERTAIN,
            "reason": (
                "The opportunity has citizenship or residency restrictions "
                "that are not specified in the user profile."
            )
        }

    return {
        "status": EligibilityStatus.UNCERTAIN,
        "reason": "The requirements need further evaluation."
    }
