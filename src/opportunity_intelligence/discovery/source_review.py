
"""Review, approve, and reject discovered opportunity sources."""

import argparse
import json

from datetime import datetime, timezone
from pathlib import Path

import yaml

from opportunity_intelligence.discovery.source_registry import (
    DEFAULT_CONFIG,
    DEFAULT_DISCOVERED_CONFIG,
    Source,
    load_sources,
    normalize_url
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_CANDIDATES_FILE = (
    PROJECT_ROOT / "data" / "processed" / "source_candidates.json"
)


def load_candidate_data(
    candidates_file: Path = DEFAULT_CANDIDATES_FILE
) -> dict:
    """Load the persisted source candidate review file."""

    if not candidates_file.exists():
        raise FileNotFoundError(
            f"Candidate file not found: {candidates_file}"
        )

    with candidates_file.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict) or not isinstance(
        data.get("candidates"), list
    ):
        raise ValueError("Invalid source candidate file.")

    return data


def save_candidate_data(
    data: dict,
    candidates_file: Path = DEFAULT_CANDIDATES_FILE
) -> None:
    """Save candidate decisions without discarding discovery metadata."""

    data["total_candidates"] = len(data["candidates"])

    candidates_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with candidates_file.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def find_candidate(
    source_id: str,
    candidates_file: Path = DEFAULT_CANDIDATES_FILE
) -> tuple[dict, dict]:
    """Find a candidate by ID and return it with its parent data."""

    data = load_candidate_data(candidates_file)

    for candidate in data["candidates"]:
        if candidate.get("id") == source_id:
            return candidate, data

    raise ValueError(
        f"Source candidate not found: {source_id}"
    )


def list_pending_candidates(
    candidates_file: Path = DEFAULT_CANDIDATES_FILE
) -> list[dict]:
    """Return candidates that still require a review decision."""

    data = load_candidate_data(candidates_file)

    return [
        candidate
        for candidate in data["candidates"]
        if candidate.get("status") == "pending"
    ]


def save_discovered_source(
    source: Source,
    discovered_config_path: Path = DEFAULT_DISCOVERED_CONFIG
) -> None:
    """Add an approved source to the discovered source registry."""

    existing_sources = []

    if discovered_config_path.exists():
        with discovered_config_path.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = yaml.safe_load(file)

        if not isinstance(data, dict) or not isinstance(
            data.get("sources"), list
        ):
            raise ValueError(
                "Invalid discovered source registry."
            )

        existing_sources = data["sources"]

    existing = load_sources(
        config_path=DEFAULT_CONFIG,
        discovered_config_path=discovered_config_path
    )

    for registered_source in existing:
        if registered_source.id == source.id:
            raise ValueError(
                f"Source ID already registered: {source.id}"
            )

        if normalize_url(str(registered_source.url)) == normalize_url(
            str(source.url)
        ):
            raise ValueError(
                f"Source URL already registered: {source.url}"
            )

    existing_sources.append(
        source.model_dump(mode="json")
    )

    discovered_config_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with discovered_config_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        yaml.safe_dump(
            {"sources": existing_sources},
            file,
            sort_keys=False,
            allow_unicode=True
        )


def approve_source_candidate(
    source_id: str,
    candidates_file: Path = DEFAULT_CANDIDATES_FILE,
    discovered_config_path: Path = DEFAULT_DISCOVERED_CONFIG,
    enabled: bool = True,
    review_notes: str | None = None
) -> Source:
    """Approve a pending candidate and register it."""

    candidate, data = find_candidate(
        source_id,
        candidates_file
    )

    if candidate.get("status") != "pending":
        raise ValueError(
            f"Candidate is not pending: {candidate.get('status')}"
        )

    source = Source.model_validate({
        "id": candidate["id"],
        "name": candidate["name"],
        "url": candidate["url"],
        "region": candidate["region"],
        "source_type": candidate["source_type"],
        "categories": candidate["categories"],
        "enabled": enabled,
        "notes": candidate.get("notes")
    })

    # Check both curated and discovered registries before writing.
    save_discovered_source(
        source,
        discovered_config_path
    )

    candidate["status"] = "approved"
    candidate["enabled"] = enabled
    candidate["reviewed_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    candidate["review_notes"] = review_notes

    save_candidate_data(
        data,
        candidates_file
    )

    return source


def reject_source_candidate(
    source_id: str,
    reason: str,
    candidates_file: Path = DEFAULT_CANDIDATES_FILE
) -> dict:
    """Reject a pending candidate and preserve the reason."""

    if not reason.strip():
        raise ValueError("A rejection reason is required.")

    candidate, data = find_candidate(
        source_id,
        candidates_file
    )

    if candidate.get("status") != "pending":
        raise ValueError(
            f"Candidate is not pending: {candidate.get('status')}"
        )

    candidate["status"] = "rejected"
    candidate["enabled"] = False
    candidate["reviewed_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    candidate["review_notes"] = reason.strip()

    save_candidate_data(
        data,
        candidates_file
    )

    return candidate


def print_pending_candidates() -> None:
    """Print pending candidates in a readable format."""

    candidates = list_pending_candidates()

    if not candidates:
        print("No pending source candidates.")
        return

    for candidate in candidates:
        print(
            f"\nID: {candidate['id']}\n"
            f"Name: {candidate['name']}\n"
            f"URL: {candidate['url']}\n"
            f"Region: {candidate['region']}\n"
            f"Type: {candidate['source_type']}\n"
            f"Score: {candidate.get('discovery_score', 0)}\n"
            f"Categories: {', '.join(candidate['categories'])}"
        )


def main() -> None:
    """Provide basic command-line source review operations."""

    parser = argparse.ArgumentParser(
        description="Review discovered opportunity sources."
    )

    parser.add_argument(
        "action",
        choices=["list", "approve", "reject"]
    )

    parser.add_argument(
        "source_id",
        nargs="?"
    )

    parser.add_argument(
        "--reason",
        default=None
    )

    parser.add_argument(
        "--disabled",
        action="store_true",
        help="Approve the source but leave it disabled."
    )

    args = parser.parse_args()

    if args.action == "list":
        print_pending_candidates()
        return

    if not args.source_id:
        parser.error("A source ID is required for this action.")

    if args.action == "approve":
        source = approve_source_candidate(
            args.source_id,
            enabled=not args.disabled
        )

        print(f"Approved source: {source.name}")
        print(f"Enabled: {source.enabled}")

    elif args.action == "reject":
        if not args.reason:
            parser.error(
                "Rejection requires --reason."
            )

        reject_source_candidate(
            args.source_id,
            args.reason
        )

        print(f"Rejected source: {args.source_id}")


if __name__ == "__main__":
    main()
