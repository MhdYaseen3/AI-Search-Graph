"""Validation and correction layer for parsed resume data.

Detects suspicious extractions and common errors:
- Education/Certifications confusion
- Experience/Project description mixing
- Invalid date ranges
- Duplicate records
- Empty or incomplete fields
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.schemas.resume_parser import (
    EducationItem,
    ExperienceItem,
    ParsedResume,
    ProjectItem,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of parsing validation."""
    is_valid: bool
    warnings: list[str]
    errors: list[str]
    corrected_resume: ParsedResume | None = None


class ResumeValidationService:
    """Validates parsed resume data for consistency and correctness."""

    # Common words in certifications
    CERT_KEYWORDS = (
        "certified", "certificate", "certification", "aws", "gcp", "azure",
        "comptia", "cissp", "ccna", "ckad", "cka", "scrum",
    )

    # Common words that indicate achievements
    ACHIEVEMENT_KEYWORDS = (
        "award", "honor", "recognition", "dean", "scholarship", "grant",
        "published", "patent",
    )

    def validate(self, parsed: ParsedResume) -> ValidationResult:
        """Validate a ParsedResume and attempt corrections.

        Returns:
            ValidationResult with warnings/errors and optionally corrected resume
        """
        warnings: list[str] = []
        errors: list[str] = []

        # Validate each section
        self._validate_experiences(parsed.experiences, warnings, errors)
        self._validate_education(parsed.education, warnings, errors)
        self._validate_projects(parsed.projects, warnings, errors)
        self._validate_skills(parsed.skills, warnings, errors)
        self._validate_technologies(parsed.technologies, warnings, errors)

        # Cross-validation
        self._validate_consistency(parsed, warnings, errors)

        # Attempt corrections if possible
        corrected = None
        if warnings:  # Only correct if there are warnings but no critical errors
            corrected = self._attempt_corrections(parsed, warnings)

        is_valid = len(errors) == 0
        if not is_valid:
            logger.warning("Resume validation failed: %s", errors)
        elif warnings:
            logger.info("Resume validation passed with warnings: %s", warnings)
        else:
            logger.info("Resume validation passed with no issues")

        return ValidationResult(
            is_valid=is_valid,
            warnings=warnings,
            errors=errors,
            corrected_resume=corrected,
        )

    def _validate_experiences(
        self,
        experiences: list[ExperienceItem],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate experience entries."""
        if not experiences:
            return

        seen = set()
        for i, exp in enumerate(experiences):
            # Check for empty required fields
            if not exp.company or not exp.company.strip():
                errors.append(f"Experience {i}: Missing company name")
            if not exp.role or not exp.role.strip():
                warnings.append(f"Experience {i}: Missing role/title")

            # Check for duplicates
            key = (exp.company or "", exp.role or "")
            if key in seen:
                warnings.append(f"Experience {i}: Likely duplicate of earlier entry")
            else:
                seen.add(key)

            # Validate date range
            if exp.start_date and exp.end_date:
                if not self._is_valid_date_range(exp.start_date, exp.end_date):
                    warnings.append(
                        f"Experience {i}: Suspicious date range "
                        f"({exp.start_date} to {exp.end_date})"
                    )

            # Check if description looks like project text
            if exp.description:
                if self._looks_like_project_text(exp.description):
                    warnings.append(
                        f"Experience {i}: Description may contain project content"
                    )

    def _validate_education(
        self,
        education: list[EducationItem],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate education entries."""
        if not education:
            return

        for i, edu in enumerate(education):
            # Check for institution
            if not edu.institution or not edu.institution.strip():
                warnings.append(f"Education {i}: Missing institution name")

            # Check for degree
            if not edu.degree or not edu.degree.strip():
                warnings.append(f"Education {i}: Missing degree information")

            # Check if this looks like a certification instead
            if edu.institution or edu.degree:
                combined = f"{edu.institution} {edu.degree}".lower()
                if any(kw in combined for kw in self.CERT_KEYWORDS):
                    warnings.append(
                        f"Education {i}: May actually be a certification "
                        f"({edu.institution} {edu.degree})"
                    )

            # Validate graduation year format
            if edu.expected_graduation:
                if not re.match(r"^\d{4}$", edu.expected_graduation.strip()):
                    warnings.append(
                        f"Education {i}: Invalid graduation year format "
                        f"({edu.expected_graduation})"
                    )

            # Validate GPA/CGPA format
            if edu.cgpa:
                if not re.match(r"^\d+(?:\.\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?$", edu.cgpa):
                    warnings.append(
                        f"Education {i}: Invalid GPA format ({edu.cgpa})"
                    )

    def _validate_projects(
        self,
        projects: list[ProjectItem],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate project entries."""
        if not projects:
            return

        for i, proj in enumerate(projects):
            # Check for title
            if not proj.title or not proj.title.strip():
                errors.append(f"Project {i}: Missing project name/title")

            # Check if title is too long (suspicious)
            if proj.title and len(proj.title) > 120:
                warnings.append(
                    f"Project {i}: Title unusually long ({len(proj.title)} chars), "
                    "may contain description"
                )

            # Check if title contains dates (suspicious)
            if proj.title and re.search(r"\d{4}|\bjan\b|\bfeb\b", proj.title.lower()):
                warnings.append(
                    f"Project {i}: Title contains date information, may be misparsed"
                )

    def _validate_skills(
        self,
        skills: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate skills list."""
        if not skills:
            return

        for i, skill in enumerate(skills):
            # Check for suspiciously long "skills"
            if len(skill) > 100:
                warnings.append(
                    f"Skill {i}: Entry unusually long ({len(skill)} chars), "
                    "may be description text"
                )

            # Check for newlines (should have been split)
            if "\n" in skill:
                warnings.append(
                    f"Skill {i}: Contains newline, may be multiple skills"
                )

    def _validate_technologies(
        self,
        technologies: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Validate technologies list."""
        # Generally more flexible, but check for obvious errors
        if not technologies:
            return

        for i, tech in enumerate(technologies):
            if len(tech) > 50:
                warnings.append(
                    f"Technology {i}: Entry unusually long ({len(tech)} chars)"
                )

    def _validate_consistency(
        self,
        parsed: ParsedResume,
        warnings: list[str],
        errors: list[str],
    ) -> None:
        """Cross-validate different sections for consistency."""
        # Check if sections are completely empty
        has_experience = bool(parsed.experiences)
        has_education = bool(parsed.education)
        has_skills = bool(parsed.skills or parsed.technologies)

        if not any([has_experience, has_education, has_skills]):
            errors.append("Resume contains no structured data (no experience, education, or skills)")

        # Check if summary looks like it came from wrong section
        if parsed.summary:
            if len(parsed.summary) > 1000:
                warnings.append(
                    "Summary unusually long, may contain multiple sections"
                )

    def _is_valid_date_range(self, start: str, end: str) -> bool:
        """Check if start date is before end date."""
        # Extract years
        start_year_match = re.search(r"\d{4}", start)
        end_year_match = re.search(r"\d{4}", end)

        if not (start_year_match and end_year_match):
            return True  # Can't validate, assume OK

        start_year = int(start_year_match.group())
        end_year = int(end_year_match.group())

        # Allow end_year >= start_year
        if end_year < start_year:
            return False

        # Check for impossible dates
        current_year = 2024
        if start_year > current_year + 1 or end_year > current_year + 1:
            return False

        if start_year < 1950:  # Unlikely to have experience from 1950
            return False

        return True

    def _looks_like_project_text(self, text: str) -> bool:
        """Heuristic: check if text looks like project description."""
        # Project descriptions often have these patterns
        project_keywords = (
            "built", "developed", "created", "implemented", "designed",
            "architected", "deployed", "launched", "github", "url",
        )

        text_lower = text.lower()
        keyword_count = sum(
            1 for kw in project_keywords
            if kw in text_lower
        )

        # If multiple project keywords and reasonable length, might be project text
        return keyword_count >= 2

    def _attempt_corrections(
        self,
        parsed: ParsedResume,
        warnings: list[str],
    ) -> ParsedResume:
        """Attempt to correct common parsing issues.

        Returns corrected ParsedResume if corrections were made, else returns
        a copy of the original.
        """
        corrected = parsed.model_copy()

        # Split skills that contain newlines
        if corrected.skills:
            corrected_skills = []
            for skill in corrected.skills:
                if "\n" in skill:
                    corrected_skills.extend(s.strip() for s in skill.split("\n") if s.strip())
                else:
                    corrected_skills.append(skill)
            corrected.skills = corrected_skills

        return corrected
