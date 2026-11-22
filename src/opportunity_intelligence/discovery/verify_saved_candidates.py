
"""Verify candidates already stored in the source review queue."""

import argparse
import json
from pathlib import Path

from opportunity_intelligence.discovery.source_verifier import (
    verify_candidates,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CANDIDATES_FILE = (
    PROJECT_ROOT / "data" / "processed" / "source_candidates.json"
)


def load_candidates() -> list[dict]:
    """Load candidates from the persistent review queue."""

    if not CANDIDATES_FILE.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {CANDIDATES_FILE}"
        )

    with CANDIDATES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data.get("candidates", [])


def save_candidates(candidates: list[dict]) -> None:
    """Save candidates without discarding their review history."""

    CANDIDATES_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "total_candidates": len(candidates),
        "candidates": candidates,
    }

    temporary_file = CANDIDATES_FILE.with_suffix(".tmp")

    with temporary_file.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)

    temporary_file.replace(CANDIDATES_FILE)


def run_saved_candidate_verification(
    limit: int | None = None,
    refresh: bool = False,
) -> list[dict]:
    """Verify pending candidates that have not already been checked."""

    candidates = load_candidates()

    candidates_to_verify = [
        candidate
        for candidate in candidates
        if candidate.get("status", "pending") == "pending"
        and (
            refresh
            or "page_verification" not in candidate
        )
    ]

    if limit is not None:
        candidates_to_verify = candidates_to_verify[:limit]

    if not candidates_to_verify:
        print("No candidates require verification.")
        return candidates

    print(f"Candidates to verify: {len(candidates_to_verify)}")

    verified = verify_candidates(
        candidates_to_verify,
        delay_seconds=1.0,
    )

    # Match results by URL so the original candidate records are updated.
    verified_by_url = {
        candidate["url"]: candidate
        for candidate in verified
    }

    for index, candidate in enumerate(candidates):
        updated = verified_by_url.get(candidate["url"])

        if updated is not None:
            candidates[index] = updated

    save_candidates(candidates)

    classifications = {}

    for candidate in verified:
        classification = candidate.get(
            "page_verification", {}
        ).get("classification", "unavailable")

        classifications[classification] = (
            classifications.get(classification, 0) + 1
        )

    print("\nVerification results:")

    for classification, count in sorted(classifications.items()):
        print(f"  {classification}: {count}")

    print(f"\nReview queue updated: {CANDIDATES_FILE}")

    return candidates


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify saved opportunity source candidates."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of candidates to verify.",
    )

    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Reverify candidates that already have verification results.",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1.")

    run_saved_candidate_verification(
        limit=args.limit,
        refresh=args.refresh,
    )
