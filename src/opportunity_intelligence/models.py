
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, HttpUrl, Field


class OpportunityCategory(str, Enum):
    RESEARCH = "Research"
    INTERNSHIP = "Internship"
    COOP = "Co-op"
    FELLOWSHIP = "Fellowship"
    UNIVERSITY_EMPLOYMENT = "University Employment"
    GOVERNMENT = "Government"
    OTHER = "Other"


class OpportunityType(str, Enum):
    PROGRAM = "Program"
    INDIVIDUAL = "Individual Position"
    DIRECTORY = "Opportunity Directory"
    UNKNOWN = "Unknown"


class OpportunityStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"
    UPCOMING = "Upcoming"
    UNKNOWN = "Unknown"


class Opportunity(BaseModel):
    """Represent a discovered employment or research opportunity."""

    title: str
    organization: str

    category: OpportunityCategory
    opportunity_type: OpportunityType = OpportunityType.UNKNOWN

    field: list[str] = Field(default_factory=list)

    location: Optional[str] = None
    work_mode: Optional[str] = None

    description: Optional[str] = None

    requirements: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    compensation: Optional[str] = None
    duration: Optional[str] = None

    start_date: Optional[date] = None
    deadline: Optional[date] = None

    eligibility: Optional[str] = None

    application_url: Optional[HttpUrl] = None
    source_url: HttpUrl
    related_source_urls: list[HttpUrl] = Field(default_factory=list)

    date_discovered: date = Field(default_factory=date.today)
    last_verified: Optional[datetime] = None

    status: OpportunityStatus = OpportunityStatus.UNKNOWN
