
import json

from opportunity_intelligence.storage.database import (
    DEFAULT_DATABASE,
    get_connection,
)

LIST_FIELDS = {
    "field",
    "evidence",
    "requirements",
    "preferred_skills",
    "related_source_urls",
}


def merge_records(connection, keep_id, remove_id, overrides):
    keep = connection.execute(
        "SELECT * FROM opportunities WHERE id = ?", (keep_id,)
    ).fetchone()

    duplicate = connection.execute(
        "SELECT * FROM opportunities WHERE id = ?", (remove_id,)
    ).fetchone()

    if keep is None or duplicate is None:
        raise ValueError(f"Missing record: {keep_id} or {remove_id}")

    keep = dict(keep)
    duplicate = dict(duplicate)

    if keep["source_url"] != duplicate["source_url"]:
        raise ValueError("Source URLs differ. Merge cancelled.")

    for field in LIST_FIELDS:
        values = [
            *json.loads(keep[field] or "[]"),
            *json.loads(duplicate[field] or "[]"),
        ]
        keep[field] = json.dumps(
            list(dict.fromkeys(values)),
            ensure_ascii=False,
        )

    for field in keep:
        if field in LIST_FIELDS or field in {
            "id", "created_at", "updated_at"
        }:
            continue

        if keep[field] in (None, "") and duplicate[field] not in (None, ""):
            keep[field] = duplicate[field]

    alternate_url = duplicate["application_url"]
    preferred_url = overrides["application_url"]

    if alternate_url and alternate_url != preferred_url:
        evidence = json.loads(keep["evidence"] or "[]")
        note = f"Additional application information page: {alternate_url}"
        if note not in evidence:
            evidence.append(note)
        keep["evidence"] = json.dumps(evidence, ensure_ascii=False)

    keep.update(overrides)

    columns = [
        row["name"]
        for row in connection.execute(
            "PRAGMA table_info(opportunities)"
        )
        if row["name"] not in {"id", "created_at", "updated_at"}
    ]

    assignments = ", ".join(f"{column} = ?" for column in columns)

    connection.execute(
        f"UPDATE opportunities SET {assignments}, "
        "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        [keep[column] for column in columns] + [keep_id],
    )

    connection.execute(
        "DELETE FROM opportunities WHERE id = ?", (remove_id,)
    )

    print(f"Merged record {remove_id} into {keep_id}.")


def main():
    with get_connection(DEFAULT_DATABASE) as connection:
        federal = connection.execute(
            "SELECT title FROM opportunities WHERE id = 2"
        ).fetchone()

        if federal is None or federal["title"] != "Federal Internships":
            raise ValueError("Unexpected record at ID 2. No changes made.")

        merge_records(
            connection,
            4,
            1,
            {
                "title": "Professional Experience Year Co-op Program (PEY Co-op)",
                "organization": "University of Toronto Faculty of Applied Science & Engineering",
                "category": "Co-op",
                "application_url": "https://engineering.utoronto.ca/pey-co-op",
            },
        )

        merge_records(
            connection,
            5,
            3,
            {
                "title": "Dean’s Undergraduate Student Summer Research Pivot Fellowship",
                "organization": "University of Toronto",
                "category": "Fellowship",
                "application_url": "https://undergradresearch.utoronto.ca/fellowships/deans-graduate-student-summer-research-pivot-fellowship",
            },
        )

        connection.execute(
            "DELETE FROM opportunities WHERE id = 2"
        )
        print("Removed the generic Federal Internships portal.")


if __name__ == "__main__":
    main()
