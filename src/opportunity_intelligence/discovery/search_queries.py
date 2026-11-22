
"""Targeted search queries for discovering opportunity sources.

Queries prioritize reusable directories, portals, and program pages.
Canada and the United States receive the most coverage.
"""

SEARCH_QUERIES = [
    # Canada
    {
        "id": "ca_research_directories",
        "query": "Canada undergraduate research opportunity directories university summer research programs",
        "region": "Canada",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "ca_cs_math_research",
        "query": "Canadian universities computer science mathematics undergraduate research programs opportunities",
        "region": "Canada",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "ca_research_programs",
        "query": "Canada undergraduate summer research programs NSERC USRA university program listings",
        "region": "Canada",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "ca_internship_coop_portals",
        "query": "Canadian university undergraduate internship co-op job portals career opportunities",
        "region": "Canada",
        "category": "internship",
        "priority": 1,
    },
    {
        "id": "ca_student_employment",
        "query": "Canada university student employment job boards undergraduate campus jobs",
        "region": "Canada",
        "category": "university_employment",
        "priority": 2,
    },
    {
        "id": "ca_government_jobs",
        "query": "Canada federal provincial government student employment internship programs undergraduate",
        "region": "Canada",
        "category": "government",
        "priority": 1,
    },
    {
        "id": "ca_fellowships",
        "query": "Canada undergraduate research fellowships funding programs university students",
        "region": "Canada",
        "category": "fellowship",
        "priority": 2,
    },

    # United States
    {
        "id": "us_reu_directories",
        "query": "United States undergraduate research REU program directories searchable listings",
        "region": "US",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "us_cs_math_research",
        "query": "United States university computer science mathematics undergraduate research programs",
        "region": "US",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "us_summer_research",
        "query": "United States undergraduate summer research program directories university students",
        "region": "US",
        "category": "research",
        "priority": 1,
    },
    {
        "id": "us_internship_portals",
        "query": "United States undergraduate computer science data science internship career portals",
        "region": "US",
        "category": "internship",
        "priority": 1,
    },
    {
        "id": "us_student_employment",
        "query": "United States university student employment campus jobs undergraduate job boards",
        "region": "US",
        "category": "university_employment",
        "priority": 2,
    },
    {
        "id": "us_government_internships",
        "query": "United States federal government undergraduate student internship programs career portals",
        "region": "US",
        "category": "government",
        "priority": 1,
    },
    {
        "id": "us_fellowships",
        "query": "United States undergraduate research fellowships funding programs university students",
        "region": "US",
        "category": "fellowship",
        "priority": 2,
    },

    # International
    {
        "id": "intl_research_directories",
        "query": "international undergraduate research opportunity directories university programs",
        "region": "International",
        "category": "research",
        "priority": 2,
    },
    {
        "id": "intl_research_internships",
        "query": "international undergraduate computer science mathematics research internship programs",
        "region": "International",
        "category": "internship",
        "priority": 2,
    },
    {
        "id": "intl_fellowships",
        "query": "international undergraduate research fellowships university funding programs",
        "region": "International",
        "category": "fellowship",
        "priority": 2,
    },
    {
        "id": "intl_student_jobs",
        "query": "international university undergraduate student internship employment opportunity portals",
        "region": "International",
        "category": "university_employment",
        "priority": 3,
    },
]
