"""Schemas for candidate comparison functionality."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateComparisonData(BaseModel):
    """Structured data for a single candidate in comparison."""

    candidate_id: str
    full_name: str
    email: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    experiences: list[dict[str, Any]] = Field(default_factory=list)
    experience_years: float | None = None


class ComparisonMetrics(BaseModel):
    """Objective comparison metrics between candidates."""

    skill_overlap: int = Field(description="Percentage of shared skills between candidates")
    skill_coverage: int = Field(description="Percentage of unique skills covered")
    technology_overlap: int = Field(description="Percentage of shared technologies")
    total_experience_diff: float | None = Field(description="Difference in years of experience")
    project_count_diff: int = Field(description="Difference in number of projects")


class ComparisonResult(BaseModel):
    """Result of comparing multiple candidates."""

    candidates: list[CandidateComparisonData]
    metrics: dict[str, ComparisonMetrics] = Field(default_factory=dict)
    ai_analysis: str | None = Field(default=None, description="AI-generated comparative analysis")
    recommendation: str | None = Field(default=None, description="Hiring recommendation based on comparison")
    error: str | None = Field(default=None, description="Error message if comparison failed")


class ComparisonRequest(BaseModel):
    """Request for candidate comparison."""

    candidate_ids: list[str] = Field(..., min_length=2, max_length=3, description="IDs of candidates to compare (2-3)")
