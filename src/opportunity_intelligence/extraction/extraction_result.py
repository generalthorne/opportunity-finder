
"""Models for the opportunity extraction process."""

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from opportunity_intelligence.models import OpportunityCategory


class OpportunityExtractionResult(BaseModel):
    """Represent one actual opportunity extracted from a webpage."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    organization: str | None = None

    category: OpportunityCategory | None = None
    opportunity_type: str = "Unknown"

    field: list[str] = Field(default_factory=list)

    location: str | None = None
    work_mode: str | None = None
    description: str | None = None

    requirements: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    compensation: str | None = None
    duration: str | None = None

    start_date: str | None = None
    deadline: str | None = None

    start_date_text: str | None = None
    deadline_text: str | None = None

    eligibility: str | None = None
    application_url: HttpUrl | None = None

    evidence: list[str] = Field(default_factory=list)


class PageExtractionResult(BaseModel):
    """Represent all opportunities extracted from one webpage."""

    model_config = ConfigDict(extra="forbid")

    is_opportunity_page: bool
    confidence: float = Field(ge=0.0, le=1.0)

    opportunities: list[OpportunityExtractionResult] = Field(
        default_factory=list
    )

    reasoning: str | None = None
