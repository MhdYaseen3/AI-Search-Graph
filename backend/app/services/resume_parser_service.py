"""
Resume Parser Service.

Rule-based / regex extraction of structured fields from raw resume text.
No external NLP / LLM dependency — designed to run as a deterministic
pre-processing step before the text (and parsed entities) are written
into the Neo4j knowledge graph.

Usage:
    from app.services.resume_parser_service import ResumeParserService

    parser = ResumeParserService()
    parsed = parser.parse(raw_text)
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from app.schemas.resume_parser import (
    EducationItem,
    ExperienceItem,
    ParsedResume,
    ProjectItem,
)

# ---------------------------------------------------------------------------
# Reference data used by the rule-based heuristics
# ---------------------------------------------------------------------------

# Canonical section name -> set of header strings (lowercase, no punctuation)
# that should be recognised as the start of that section.
SECTION_SYNONYMS: Dict[str, List[str]] = {
    "skills": [
        "skills",
        "technical skills",
        "core skills",
        "key skills",
        "skill set",
        "skills & tools",
        "technologies",
        "technical proficiencies",
        "competencies",
        "core competencies",
    ],
    "projects": [
        "projects",
        "personal projects",
        "academic projects",
        "project experience",
        "key projects",
        "selected projects",
        "professional projects",
    ],
    "education": [
        "education",
        "academic background",
        "educational qualification",
        "educational qualifications",
        "academics",
        "educational background",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internship experience",
        "internships",
        "work history",
        "career history",
        "professional history",
        "employment",
        "career",
        "relevant experience",
    ],
    "summary": [
        "summary",
        "professional summary",
        "profile",
        "professional profile",
        "about me",
        "objective",
        "career objective",
        "career summary",
    ],
    "certifications": [
        "certifications",
        "certificates",
        "licenses & certifications",
        "professional certifications",
        "courses",
        "training",
    ],
    "achievements": [
        "achievements",
        "awards",
        "honors",
        "accomplishments",
        "recognition",
    ],
    "languages": [
        "languages",
        "language proficiency",
        "language skills",
        "languages known",
    ],
    "publications": [
        "publications",
        "papers",
        "research",
    ],
    "volunteering": [
        "volunteering",
        "volunteer experience",
        "volunteer work",
    ],
    "leadership": [
        "leadership",
        "leadership experience",
    ],
    "extracurricular": [
        "extracurricular",
        "extracurricular activities",
        "activities",
    ],
}

# Canonical technology/tool keyword bank: lowercase match key -> clean
# display name for the graph node. Used (a) as a fallback when no explicit
# "Skills" section header is found, and (b) to detect `technologies`
# (recognised tech-stack terms mentioned anywhere in the resume or in
# project descriptions) — a narrower, machine-identified subset distinct
# from the candidate's self-listed `skills`.
TECH_KEYWORD_DISPLAY: Dict[str, str] = {
    "python": "Python", "java": "Java", "javascript": "JavaScript",
    "typescript": "TypeScript", "c++": "C++", "c#": "C#", "go": "Go", "rust": "Rust",
    "react": "React", "angular": "Angular", "vue": "Vue.js", "next.js": "Next.js",
    "node.js": "Node.js", "express": "Express.js",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "spring boot": "Spring Boot", "spring": "Spring",
    "html": "HTML", "css": "CSS", "tailwind css": "Tailwind CSS", "tailwind": "Tailwind CSS",
    "bootstrap": "Bootstrap",
    "sql": "SQL", "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "neo4j": "Neo4j", "redis": "Redis", "sqlite": "SQLite",
    "docker": "Docker", "kubernetes": "Kubernetes", "aws": "AWS", "azure": "Azure",
    "gcp": "Google Cloud Platform", "terraform": "Terraform",
    "git": "Git", "github": "GitHub", "gitlab": "GitLab", "ci/cd": "CI/CD", "linux": "Linux",
    "pandas": "Pandas", "numpy": "NumPy", "pytorch": "PyTorch", "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn", "machine learning": "Machine Learning",
    "deep learning": "Deep Learning", "nlp": "NLP", "data analysis": "Data Analysis",
    "rest api": "REST API", "graphql": "GraphQL", "microservices": "Microservices",
    "pymupdf": "PyMuPDF", "ollama": "Ollama",
        "iot": "IoT", "ai": "AI",
}

DEGREE_KEYWORDS_PATTERN = re.compile(
    r"\b(b\.?\s?tech|m\.?\s?tech|b\.?\s?e\.?|m\.?\s?e\.?|b\.?\s?sc\.?|m\.?\s?sc\.?|"
    r"b\.?\s?a\.?|m\.?\s?a\.?|b\.?\s?s\.?|m\.?\s?s\.?|ph\.?\s?d\.?|mba|bba|"
    r"bachelor(?:'s)?(?:\s+of\s+\w+)?|master(?:'s)?(?:\s+of\s+\w+)?|"
    r"doctorate|diploma|associate(?:'s)?\s+degree)\b",
    re.IGNORECASE,
)

INSTITUTION_KEYWORDS_PATTERN = re.compile(
    r"\b(university|college|institute|polytechnic|school of|academy)\b",
    re.IGNORECASE,
)

# Pulls out just the institution name (e.g. "XYZ University") from a longer
# line like "B.Tech in Computer Science, XYZ University, 2022".
INSTITUTION_NAME_PATTERN = re.compile(
    r"([A-Z][A-Za-z&'.]*(?:\s+(?:of|and|the|for)\s+[A-Za-z]+|\s+[A-Z][A-Za-z&'.]*)*"
    r"\s+(?:University|College|Institute(?:\s+of\s+[A-Za-z]+)?|Academy|Polytechnic))"
)

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9.-]+")

# Matches common phone formats: optional country code, optional parentheses,
# digits separated by spaces/dots/dashes. Over-matches slightly by design;
# digit-count validation in _extract_phone() filters out junk.
PHONE_CANDIDATE_PATTERN = re.compile(
    r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,5}\)?[\s.-]?){2,5}\d{2,4}"
)

BULLET_PREFIX_PATTERN = re.compile(r"^[\-\*\u2022\u25aa\u25cf\u2023\u2043►▪]\s*")


class ResumeParserService:
    """Stateless service that converts raw resume text into a ParsedResume."""

    def parse(self, raw_text: str) -> ParsedResume:
        """Run the full extraction pipeline and return a ParsedResume.

        Each field is extracted independently and defensively — a failure
        or miss on one field never blocks extraction of the others.
        """
        text = (raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
        sections = self._split_sections(text)

        candidate_name = self._safe(self._extract_name, text)
        email = self._safe(self._extract_email, text)
        phone = self._safe(self._extract_phone, text)
        summary = self._safe(self._extract_summary, sections)
        skills = self._safe(self._extract_skills, sections, text) or []
        projects = self._safe(self._extract_projects, sections) or []
        education = self._safe(
            self._extract_education,
            sections,
        ) or []
        
        experiences = self._safe(
            self._extract_experience,
            sections,
        ) or []

        technologies = self._safe(
            self._extract_technologies,
            text,
            projects,
        ) or []

        return ParsedResume(
            candidate_name=candidate_name,
            email=email,
            phone=phone,
            summary=summary,
            skills=skills,
            projects=projects,
            education=education,
            experiences=experiences,
            technologies=technologies,
        )

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    def _split_sections(self, text: str) -> Dict[str, str]:
        """Split resume text into named sections using header-line detection."""
        lines = text.split("\n")
        sections: Dict[str, List[str]] = {"header": []}
        current = "header"

        for line in lines:
            inline_headers = self._find_inline_headers(line)
            if inline_headers:
                prefix = line[: inline_headers[0][0]].strip()
                if prefix:
                    sections.setdefault(current, []).append(prefix)
                for index, (start, end, canonical) in enumerate(inline_headers):
                    current = canonical
                    sections.setdefault(current, [])
                    next_start = (
                        inline_headers[index + 1][0]
                        if index + 1 < len(inline_headers)
                        else len(line)
                    )
                    content = line[end:next_start].strip()
                    if content:
                        sections[current].append(content)
            else:
                sections.setdefault(current, []).append(line)

        return {name: "\n".join(content).strip() for name, content in sections.items()}

    def _match_header(self, line: str) -> Optional[str]:
        stripped = line.strip().strip(":").strip()
        if not stripped or len(stripped) > 40 or len(stripped.split()) > 5:
            return None
        normalized = self._normalize_heading(stripped)

        # Try exact match first
        for canonical, synonyms in SECTION_SYNONYMS.items():
            if normalized in synonyms:
                return canonical

        return None

    def _normalize_heading(self, value: str) -> str:
        return re.sub(r"[^a-z0-9 &/]", "", value.lower()).strip()

    def _find_inline_headers(self, line: str) -> List[tuple[int, int, str]]:
        """Find exact top-level headings, including adjacent headings on one line."""
        stripped = line.strip().strip(":").strip()
        if not stripped:
            return []
        normalized = self._normalize_heading(stripped)
        headings = [
            (synonym, canonical)
            for canonical, synonyms in SECTION_SYNONYMS.items()
            for synonym in synonyms
        ]
        headings.sort(key=lambda item: len(item[0]), reverse=True)
        matches: List[tuple[int, int, str]] = []
        for synonym, canonical in headings:
            pattern = re.compile(rf"(?<![a-z]){re.escape(synonym)}(?![a-z])")
            for match in pattern.finditer(normalized):
                if any(match.start() >= start and match.end() <= end for start, end, _ in matches):
                    continue
                matches.append((match.start(), match.end(), canonical))
        matches.sort()
        if not matches:
            return []
        # A normal content line containing a word such as "experience" is not a header.
        if len(matches) == 1 and self._match_header(stripped) is None:
            return []
        return matches

    # ------------------------------------------------------------------
    # Contact info
    # ------------------------------------------------------------------

    def _extract_email(self, text: str) -> Optional[str]:
        match = EMAIL_PATTERN.search(text)
        return match.group(0).strip().rstrip(".,;") if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        for match in PHONE_CANDIDATE_PATTERN.finditer(text):
            candidate = match.group(0).strip()
            digit_count = len(re.sub(r"\D", "", candidate))
            if 7 <= digit_count <= 15:
                return candidate
        return None

    def _extract_name(self, text: str) -> Optional[str]:
        lines = [l.strip() for l in text.split("\n")]
        non_empty = [l for l in lines if l][:6]  # name almost always near the top

        for line in non_empty:
            if EMAIL_PATTERN.search(line) or PHONE_CANDIDATE_PATTERN.search(line):
                continue
            if self._match_header(line):
                continue
            words = line.split()
            if not (1 <= len(words) <= 4):
                continue
            # Reject lines with digits or typical non-name punctuation/symbols
            if re.search(r"[\d@/|•]", line):
                continue
            if not all(re.match(r"^[A-Za-z.'\-]+$", w) for w in words):
                continue
            # Looks like a name (Title Case or ALL CAPS)
            if all(w[0].isupper() for w in words if w):
                return line.title() if line.isupper() else line
        return None

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def _extract_skills(self, sections: Dict[str, str], full_text: str) -> List[str]:
        content = sections.get("skills", "")

        if content:
            # Split on common delimiters: commas, bullets, pipes, semicolons, newlines
            raw_tokens = re.split(r"[,\n•|;\u2022\u25aa]+", content)
            skills = []
            for token in raw_tokens:
                cleaned = BULLET_PREFIX_PATTERN.sub("", token).strip(" -\t")
                # Drop sub-headers like "Languages:" sometimes embedded in this section
                cleaned = re.sub(r"^[A-Za-z &/]{2,25}:\s*", "", cleaned).strip()
                if cleaned and len(cleaned) <= 40:
                    skills.append(cleaned)
            return self._dedupe_preserve_order(skills)

        # Fallback: scan whole document for recognised technology keywords
        return self._find_known_keywords(full_text)

    # ------------------------------------------------------------------
    # Technologies
    # ------------------------------------------------------------------

    def _extract_technologies(self, full_text: str, projects: List[ProjectItem]) -> List[str]:
        """Detect recognised technology/tool keywords anywhere in the resume
        or within project descriptions.

        Distinct from `skills`: `skills` is whatever the candidate
        self-listed under a Skills/Technical Skills header (verbatim,
        unfiltered). `technologies` is a machine-identified subset useful
        for "who has hands-on experience with X" style graph queries —
        e.g. a tool only mentioned inside a project write-up, not in the
        Skills section, still shows up here.
        """
        combined = full_text + "\n" + "\n".join(p.raw_text for p in projects)
        return self._find_known_keywords(combined)

    def _find_known_keywords(self, text: str) -> List[str]:
        lowered = text.lower()
        lowered = re.sub(r"\bnode\s+js\b", "node.js", lowered)
        lowered = re.sub(r"\breact[,.]\s*js\b", "react.js", lowered)
        lowered = re.sub(r"\blot\b", "iot", lowered)
        lowered = re.sub(r"\bal\b", "ai", lowered)
        found = []
        for keyword, display_name in TECH_KEYWORD_DISPLAY.items():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                found.append(display_name)
        return self._dedupe_preserve_order(found)

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def _extract_projects(self, sections: Dict[str, str]) -> List[ProjectItem]:
        content = sections.get("projects", "")
        if not content:
            return []

        chunks = self._split_into_entries(content)
        projects = []
        for chunk in chunks:
            lines = [BULLET_PREFIX_PATTERN.sub("", l).strip() for l in chunk.split("\n") if l.strip()]
            if not lines:
                continue
            title = lines[0][:120]
            description = " ".join(lines[1:]).strip() or None
            projects.append(
                ProjectItem(title=title, description=description, raw_text=chunk.strip())
            )
        return projects

    # ------------------------------------------------------------------
    # Education
    # ------------------------------------------------------------------

    def _extract_education(self, sections: Dict[str, str]) -> List[EducationItem]:
        content = sections.get("education", "")
        if not content:
            return []

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        entries: List[List[str]] = []
        current: List[str] = []
        for line in lines:
            if current and DEGREE_KEYWORDS_PATTERN.search(line):
                entries.append(current)
                current = []
            current.append(line)
        if current:
            entries.append(current)

        education = []
        for entry_lines in entries:
            degree = next(
                (line for line in entry_lines if DEGREE_KEYWORDS_PATTERN.search(line)),
                None,
            )
            institution = next(
                (
                    line
                    for line in entry_lines
                    if INSTITUTION_KEYWORDS_PATTERN.search(line)
                ),
                None,
            )
            field_of_study = next(
                (
                    line
                    for line in entry_lines
                    if line not in {degree, institution}
                    and not re.search(
                        r"\b(?:expected graduation|graduation|cgpa|gpa|from|to)\b|\d{4}",
                        line,
                        re.IGNORECASE,
                    )
                ),
                None,
            )
            graduation_match = next(
                (
                    match
                    for line in entry_lines
                    if (match := re.search(
                        r"(?:expected\s+graduation|graduation)\s*[:\-]?\s*(\d{4})",
                        line,
                        re.IGNORECASE,
                    ))
                ),
                None,
            )
            cgpa_match = next(
                (
                    match
                    for line in entry_lines
                    if (match := re.search(
                        r"(?:cgpa|gpa)\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+)?)",
                        line,
                        re.IGNORECASE,
                    ))
                ),
                None,
            )
            if degree or institution:
                education.append(
                    EducationItem(
                        institution=institution,
                        degree=degree,
                        field_of_study=field_of_study,
                        expected_graduation=graduation_match.group(1) if graduation_match else None,
                        cgpa=cgpa_match.group(1) if cgpa_match else None,
                        raw_text="\n".join(entry_lines),
                    )
                )
        return education

    # ------------------------------------------------------------------
    # Summary / Profile / Objective
    # ------------------------------------------------------------------

    def _extract_summary(self, sections: Dict[str, str]) -> Optional[str]:
        """Extract the summary/profile/objective text from the resume."""
        content = sections.get("summary", "").strip()

        if not content:
            return None

        # Take the first 500 characters of the summary section
        # Remove leading/trailing whitespace and excessive newlines
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        summary_text = ' '.join(lines)

        # Limit to first 500 characters for reasonable length
        if len(summary_text) > 500:
            summary_text = summary_text[:500].rsplit(' ', 1)[0] + '...'

        return summary_text if summary_text else None

    # ------------------------------------------------------------------
    # Experience
    # ------------------------------------------------------------------

    def _extract_experience(
        self,
        sections: Dict[str, str],
    ) -> List[ExperienceItem]:
        """Extract structured work experience entries."""
        content = sections.get("experience", "").strip()

        if not content:
            return []

        lines = [
            line.strip()
            for line in content.split("\n")
            if line.strip()
        ]

        experiences = []
        current_lines = []

        for line in lines:
            # A new job normally starts with:
            # Company — Role
            # Company - Role
            # Company | Role
            # Company @ Role
            is_job_header = self._looks_like_experience_header(line)

            if is_job_header and current_lines and self._can_start_new_experience(current_lines, line):
                experience = self._parse_experience_entry(current_lines)

                if experience:
                    experiences.append(experience)

                current_lines = []

            current_lines.append(line)

        # Don't forget the final experience
        if current_lines:
            experience = self._parse_experience_entry(current_lines)

            if experience:
                experiences.append(experience)

        return experiences

    def _can_start_new_experience(self, current_lines: List[str], line: str) -> bool:
        """Avoid splitting a company-only header from its following role line."""
        clean = BULLET_PREFIX_PATTERN.sub("", line).strip()
        if re.search(r"\s+[—–|@-]\s+", clean):
            return True
        if clean.isupper() and not re.search(r"\b(?:duration|present|19|20\d{2})\b", clean, re.IGNORECASE):
            return True
        first = BULLET_PREFIX_PATTERN.sub("", current_lines[0]).strip()
        return not (
            len(current_lines) == 1
            and not self._has_role_keyword(first)
            and self._has_role_keyword(clean)
        )

    def _has_role_keyword(self, value: str) -> bool:
        return bool(
            re.search(
                r"\b(?:developer|engineer|intern|manager|designer|analyst|"
                r"architect|consultant|administrator|specialist|lead|"
                r"scientist|researcher|director|programmer)\b",
                value,
                re.IGNORECASE,
            )
        )

    def _looks_like_experience_header(self, line: str) -> bool:
        """Determine whether a line represents a new job/company header."""
        clean = BULLET_PREFIX_PATTERN.sub("", line).strip()

        if not clean:
            return False

        # --------------------------------------------------
        # 1. Bullet points are never job headers
        # --------------------------------------------------
        if line.startswith(("-", "*", "•", "▪", "●")):
            return False

        # --------------------------------------------------
        # 2. Date / duration lines are NEVER job headers
        # --------------------------------------------------
        date_pattern = re.compile(
            r"""
            (
                (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*
                \s+\d{4}
            )
            |
            (
                \d{4}
            )
            """,
            re.IGNORECASE | re.VERBOSE,
        )

        duration_pattern = re.compile(
            r"\b\d+\s+(?:year|years|month|months|yr|yrs|mo|mos)\b",
            re.IGNORECASE,
        )

        # Date lines are metadata for the preceding job.
        if date_pattern.search(clean):
            return False

        # --------------------------------------------------
        # 3. Strong company-role separator
        # --------------------------------------------------
        if re.search(r"\s+[—–|@]\s+", clean):
            return True

        # Hyphen separator, but only if it isn't part of a date.
        if re.search(r"\s+-\s+", clean):
            return True

        # --------------------------------------------------
        # 4. Role keyword fallback
        # --------------------------------------------------
        role_keywords = (
            r"developer|engineer|intern|manager|designer|analyst|"
            r"architect|consultant|administrator|specialist|lead|"
            r"scientist|researcher|director|programmer"
        )

        return bool(
            re.search(
                rf"\b({role_keywords})\b",
                clean,
                re.IGNORECASE,
            )
        )

    def _parse_experience_entry(
        self,
        lines: List[str],
    ) -> Optional[ExperienceItem]:
        """Parse one complete work experience entry."""
        if not lines:
            return None

        header = BULLET_PREFIX_PATTERN.sub("", lines[0]).strip()
        duration_match = re.search(
            r"\bDuration\s*:\s*([^|,;]+?)(?=\s+(?:from|until|\d{4}|[—–-])|$)",
            " ".join(lines[:2]),
            re.IGNORECASE,
        )
        duration = duration_match.group(1).strip() if duration_match else None
        header = re.sub(r"\s*Duration\s*:\s*[^|,;]+?(?=\s+(?:from|until|\d{4}|[—–-])|$)", "", header, flags=re.IGNORECASE).strip(" -|—–")

        company = None
        role = None

        # Try to split by common separators: Company — Role or Role — Company
        match = re.match(
            r"^(.*?)\s+[—–|@-]\s+(.*)$",
            header,
        )

        if match:
            left = match.group(1).strip()
            right = match.group(2).strip()

            # Heuristic: Check which side looks like a role vs company
            role_keywords = (
                r"developer|engineer|intern|manager|designer|analyst|"
                r"architect|consultant|specialist|lead|director|officer|associate|coordinator"
            )
            company_keywords = r"(inc|corp|co|ltd|llc|agency|studio|labs|group|ventures|solutions|systems|tech|startup|\bai\b)"

            left_has_role = bool(re.search(rf"\b({role_keywords})\b", left, re.IGNORECASE))
            left_has_company = bool(re.search(company_keywords, left, re.IGNORECASE))
            right_has_role = bool(re.search(rf"\b({role_keywords})\b", right, re.IGNORECASE))
            right_has_company = bool(re.search(company_keywords, right, re.IGNORECASE))

            # Assign based on heuristics
            if left_has_role and not left_has_company:
                role = left
                company = right
            elif right_has_role and not right_has_company:
                company = left
                role = right
            elif left_has_company and not left_has_role:
                company = left
                role = right
            elif right_has_company and not right_has_role:
                role = left
                company = right
            else:
                # Default: assume "Company — Role" format
                company = left
                role = right
        else:
            role_keywords = (
                r"developer|engineer|intern|manager|designer|analyst|"
                r"architect|consultant|specialist|lead"
            )

            if len(lines) > 1 and self._has_role_keyword(lines[1]):
                company = header
                role = BULLET_PREFIX_PATTERN.sub("", lines[1]).strip()
            elif re.search(rf"\b({role_keywords})\b", header, re.IGNORECASE):
                role = header
            else:
                company = header

        # --------------------------------------------------
        # Dates
        # --------------------------------------------------
        start_date = None
        end_date = None

        date_text = " ".join(lines[:3])

        date_match = re.search(
            r"([A-Za-z]{3,9}\s+\d{4})"
            r"\s*[–—-]\s*"
            r"(Present|[A-Za-z]{3,9}\s+\d{4})",
            date_text,
            re.IGNORECASE,
        )

        if date_match:
            start_date = date_match.group(1).strip()
            end_date = date_match.group(2).strip()

        # --------------------------------------------------
        # Description
        # --------------------------------------------------
        description_lines = []

        for line in lines[1:]:
            # Skip date/duration metadata
            if re.search(
                r"\b(?:19|20)\d{2}\b",
                line,
            ):
                continue

            if re.search(r"\bDuration\s*:", line, re.IGNORECASE):
                continue

            if len(lines) > 1 and line == lines[1] and role == BULLET_PREFIX_PATTERN.sub("", line).strip():
                continue

            cleaned = BULLET_PREFIX_PATTERN.sub(
                "",
                line,
            ).strip()

            if cleaned:
                description_lines.append(cleaned)

        description = (
            " ".join(description_lines)
            if description_lines
            else None
        )

        return ExperienceItem(
            company=company,
            role=role,
            description=description,
            duration=duration,
            start_date=start_date,
            end_date=end_date,
            raw_text="\n".join(lines),
        )

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _split_into_entries(self, section_text: str) -> List[str]:
        """Split a section's content into individual entries.

        Tries blank-line separation first (the common case for multi-line
        entries). If the section has no blank lines, groups consecutive
        lines by whether each line "looks like" a new entry's title
        (bulleted, or short/Title-Case) versus a continuation/description
        line — this correctly handles both a single project whose title
        and description span two lines, and multiple one-line entries
        packed back-to-back with no separator.
        """
        blocks = [b.strip() for b in re.split(r"\n\s*\n", section_text) if b.strip()]
        if len(blocks) > 1:
            return blocks

        lines = [l.strip() for l in section_text.split("\n") if l.strip()]
        if not lines:
            return [section_text.strip()] if section_text.strip() else []
        if len(lines) == 1:
            return lines

        entries: List[str] = []
        current: List[str] = []
        for line in lines:
            is_bullet = bool(BULLET_PREFIX_PATTERN.match(line))
            clean = BULLET_PREFIX_PATTERN.sub("", line).strip()
            starts_new = current and (is_bullet or self._looks_like_title(clean))
            if starts_new:
                entries.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            entries.append("\n".join(current))
        return entries

    def _looks_like_title(self, line: str) -> bool:
        """Heuristic: short, mostly-capitalized, not sentence-punctuated —
        typical of a project/degree title line rather than a description."""
        words = line.split()
        if not (1 <= len(words) <= 10):
            return False
        if line.endswith((".", ",")):
            return False
        cap_words = sum(1 for w in words if w[:1].isupper())
        return (cap_words / len(words)) >= 0.5

    def _dedupe_preserve_order(self, items: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in items:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result

    def _safe(self, fn, *args):
        try:
            return fn(*args)
        except Exception:
            return None
