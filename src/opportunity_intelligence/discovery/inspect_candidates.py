
"""Display source candidates and their page-verification evidence."""

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CANDIDATES_FILE = (
    PROJECT_ROOT / "data" / "processed" / "source_candidates.json"
)


def main() -> None:
    with CANDIDATES_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    for candidate in data.get("candidates", []):
        verification = candidate.get("page_verification")

        if not verification:
            continue

        print("\n" + "=" * 65)
        print(f"Name: {candidate.get('name')}")
        print(f"URL: {candidate.get('url')}")
        print(f"Review status: {candidate.get('status')}")
        print(f"Verification: {verification.get('status')}")
        print(f"Classification: {verification.get('classification', 'Unavailable')}")
        print(f"Score: {verification.get('score', 'N/A')}")
        print(f"HTTP status: {verification.get('http_status')}")

        print("\nPositive signals:")
        for signal in verification.get("positive_signals", []):
            print(f"  - {signal['type']}: {signal['signal']}")

        print("\nNegative signals:")
        for signal in verification.get("negative_signals", []):
            print(f"  - {signal}")

        if verification.get("error"):
            print(f"\nError: {verification['error']}")

        print("\nPage excerpt:")
        print(verification.get("page_text_excerpt", "Unavailable"))


if __name__ == "__main__":
    main()
