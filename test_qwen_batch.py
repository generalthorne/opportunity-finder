
"""Evaluate qwen3 4b on a representative batch of webpages."""

import json
import time
from pathlib import Path

from opportunity_intelligence.extraction.llm_extractor import (
    DEFAULT_MODEL,
    extract_page_with_llm,
)


INPUT_FILE = Path("data/raw/investigated_pages.json")
OUTPUT_FILE = Path("data/gemma_batch_test_results.json")

# Page indices are zero-based.
# Expected values are manually assigned for evaluation.
TEST_PAGES = {
    75: True,
}


def main():
    with INPUT_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    pages = data["pages"]

    results = []
    correct = 0
    evaluated = 0
    total_time = 0.0

    print(f"Model: {DEFAULT_MODEL}")
    print(f"Pages to test: {len(TEST_PAGES)}")
    print("=" * 65)

    for index, expected in TEST_PAGES.items():
        if index >= len(pages):
            print(f"\nSkipping page index {index}: not found.")
            continue

        page = pages[index]
        title = page.get("page_title") or "Unknown"
        page_text = page.get("page_text") or ""

        print(f"\n[{index}] {title}")

        if not page_text.strip():
            print("Skipped: no webpage text.")
            continue

        start = time.perf_counter()

        try:
            result = extract_page_with_llm(
                page_text=page_text,
                page_title=title,
                model=DEFAULT_MODEL,
            )

            elapsed = time.perf_counter() - start
            total_time += elapsed

            predicted = result.is_opportunity_page
            is_correct = predicted == expected

            evaluated += 1
            correct += int(is_correct)

            print(f"Expected: {expected}")
            print(f"Predicted: {predicted}")
            print(f"Correct: {is_correct}")
            print(f"Opportunities extracted: {len(result.opportunities)}")
            print(f"Time: {elapsed:.1f}s")

            for opportunity in result.opportunities:
                print(f"  - {opportunity.title}")
                print(f"    Organization: {opportunity.organization}")
                print(f"    Deadline: {opportunity.deadline_text or opportunity.deadline}")
                print(f"    Application URL: {opportunity.application_url}")

            results.append({
                "page_index": index,
                "page_title": title,
                "expected_classification": expected,
                "predicted_classification": predicted,
                "correct": is_correct,
                "elapsed_seconds": round(elapsed, 2),
                "result": result.model_dump(mode="json"),
                "error": None,
            })

        except Exception as error:
            elapsed = time.perf_counter() - start
            total_time += elapsed

            print(f"ERROR: {error}")

            results.append({
                "page_index": index,
                "page_title": title,
                "expected_classification": expected,
                "predicted_classification": None,
                "correct": False,
                "elapsed_seconds": round(elapsed, 2),
                "result": None,
                "error": str(error),
            })

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)

    print("\n" + "=" * 65)
    print("BATCH RESULTS")
    print("=" * 65)
    print(f"Evaluated pages: {evaluated}")
    print(f"Correct classifications: {correct}")
    print(f"Classification accuracy: {correct / evaluated:.1%}" if evaluated else "No pages evaluated.")
    print(f"Total processing time: {total_time:.1f}s")
    print(f"Average processing time: {total_time / evaluated:.1f}s" if evaluated else "")
    print(f"Detailed results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
