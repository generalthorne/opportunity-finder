
import json

from opportunity_intelligence.discovery.process_links import (
    normalize_url,
    process_raw_records,
    save_prioritized_links
)


def create_raw_record(
    source_id: str,
    links: list[dict]
) -> dict:
    return {
        "source_id": source_id,
        "source_name": "Test University",
        "url": "https://example.com",
        "region": "Canada",
        "source_type": "university",
        "status": "success",
        "links": links
    }


def test_normalize_url():
    url = "https://example.com/research/#section"

    assert normalize_url(url) == "https://example.com/research"


def test_process_raw_records(tmp_path):
    record = create_raw_record(
        "test_source",
        [
            {
                "text": "Summer Research Fellowship",
                "url": "https://example.com/fellowship"
            },
            {
                "text": "Contact Us",
                "url": "https://example.com/contact"
            }
        ]
    )

    record_file = tmp_path / "test_source.json"

    record_file.write_text(
        json.dumps(record),
        encoding="utf-8"
    )

    results = process_raw_records(tmp_path)

    assert len(results) == 1
    assert results[0]["text"] == "Summer Research Fellowship"
    assert results[0]["link_type"] == "opportunity"
    assert len(results[0]["discovered_in"]) == 1


def test_duplicate_links_are_merged(tmp_path):
    first_record = create_raw_record(
        "source_one",
        [
            {
                "text": "Summer Research Fellowship",
                "url": "https://example.com/fellowship"
            }
        ]
    )

    second_record = create_raw_record(
        "source_two",
        [
            {
                "text": "Summer Research Fellowship",
                "url": "https://example.com/fellowship/"
            }
        ]
    )

    (tmp_path / "first.json").write_text(
        json.dumps(first_record),
        encoding="utf-8"
    )

    (tmp_path / "second.json").write_text(
        json.dumps(second_record),
        encoding="utf-8"
    )

    results = process_raw_records(tmp_path)

    assert len(results) == 1
    assert len(results[0]["discovered_in"]) == 2


def test_save_prioritized_links(tmp_path):
    output_file = tmp_path / "processed" / "links.json"

    links = [
        {
            "text": "Summer Research Fellowship",
            "url": "https://example.com/fellowship",
            "relevance_score": 5
        }
    ]

    save_prioritized_links(links, output_file)

    assert output_file.exists()

    saved_data = json.loads(
        output_file.read_text(encoding="utf-8")
    )

    assert saved_data["total_links"] == 1
    assert saved_data["links"][0]["text"] == "Summer Research Fellowship"
