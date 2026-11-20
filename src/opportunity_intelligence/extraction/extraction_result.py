"""Models for the opportunity extraction process."""

from pydantic import BaseModel, Field, HttpUrl

from opportunity_intelligence.models import (
    OpportunityCategory,
    OpportunityType
)


class OpportunityExtractionResult(BaseModel):
    """Represent the result of extracting information from a webpage."""

    is_opportunity: bool

    confidence: float = Field(ge=0.0, le=1.0)

    title: str | None = None
    organization: str | None = None

    category: OpportunityCategory | None = None

    opportunity_type: OpportunityType = OpportunityType.UNKNOWN

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

    eligibility: str | None = None

    application_url: HttpUrl | None = None

    evidence: list[str] = Field(default_factory=list)
    reasoning: str | None = None