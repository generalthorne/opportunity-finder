"""Remove duplicate opportunities from extracted results."""

from opportunity_intelligence.models import Opportunity


def deduplicate_opportunities(
    opportunities: list[Opportunity]
) -> list[Opportunity]:
    """Merge duplicate opportunities while preserving their source URLs."""

    unique_opportunities = []
    opportunity_indices = {}

    for opportunity in opportunities:
        identifier = (
            opportunity.title.strip().lower(),
            opportunity.organization.strip().lower(),
            opportunity.category
        )

        if identifier not in opportunity_indices:
            opportunity_indices[identifier] = len(unique_opportunities)
            unique_opportunities.append(opportunity)
            continue

        index = opportunity_indices[identifier]
        existing = unique_opportunities[index]

        related_urls = list(existing.related_source_urls)

        urls_to_add = [
            opportunity.source_url,
            *opportunity.related_source_urls
        ]

        seen_urls = {
            str(existing.source_url),
            *(str(url) for url in related_urls)
        }

        for url in urls_to_add:
            if str(url) not in seen_urls:
                related_urls.append(url)
                seen_urls.add(str(url))

        unique_opportunities[index] = existing.model_copy(
            update={"related_source_urls": related_urls}
        )

    return unique_opportunities