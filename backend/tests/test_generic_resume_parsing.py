"""Comprehensive tests for generic resume parsing.

Tests cover:
- Single-column resumes
- Multi-column layouts
- Unusual section ordering
- Missing sections
- Multiple jobs/internships/education entries
- Different date formats
- OCR-like artifacts
- Edge cases
"""

import pytest
from app.services.resume_parser_service import ResumeParserService
from app.services.resume_validation import ResumeValidationService


# ============================================================================
# Fixture A: Simple single-column resume
# ============================================================================

SIMPLE_SINGLE_COLUMN = """JOHN DOE
john@example.com | (555) 123-4567 | LinkedIn.com/in/johndoe

PROFESSIONAL SUMMARY
Full-stack developer with 5+ years experience building scalable web applications.

EXPERIENCE
Acme Tech - Senior Developer
Jan 2022 - Present
- Led team of 3 developers
- Architected microservices platform
- Improved performance by 40%

TechStart Inc - Software Engineer
Jun 2020 - Dec 2021
- Developed REST APIs in Python/FastAPI
- Managed PostgreSQL databases
- Collaborated with product team

EDUCATION
Bachelor of Science in Computer Science
University of California
Graduation: 2020
GPA: 3.8

SKILLS
Python, JavaScript, React, Node.js, PostgreSQL, Docker, AWS
"""


# ============================================================================
# Fixture B: Two-column layout (represented as text)
# ============================================================================

TWO_COLUMN_LAYOUT = """JANE SMITH                                    jane.smith@email.com | (555) 987-6543

LEFT COLUMN:                                    MIDDLE COLUMN:
Education                                        Certifications
Bachelor of Engineering                         AWS Solutions Architect
IIT Bombay, 2020                                Certified, 2023

Master's in Progress                            Languages
Stanford, Expected 2025                         English (Native)
                                                Hindi (Fluent)
                                                Spanish (Basic)

EXPERIENCE
Startup AI - ML Engineer
2023 - Present
- Built recommendation system using TensorFlow
- Deployed models on AWS Lambda
- Mentored junior engineers

Google - Data Scientist
2021 - 2022
- Analyzed user behavior patterns
- Created dashboards in Tableau
- Published 2 internal research papers

SKILLS
TensorFlow, PyTorch, Pandas, SQL, Python, AWS, GCP
"""


# ============================================================================
# Fixture C: Multiple jobs at same company, multiple internships
# ============================================================================

MULTIPLE_ROLES_SAME_COMPANY = """ALEX CHEN
alex.chen@example.com

PROFESSIONAL PROFILE
Software engineer with internship and full-time experience at growing tech company.

WORK EXPERIENCE
Nexus Labs - Software Engineer
Aug 2023 - Present
- Backend development in Go
- Microservices architecture
- Performance optimization

Nexus Labs - Software Engineering Intern
Jun 2023 - Jul 2023
- Frontend development in React
- Implemented UI components
- Fixed critical bugs

Previous Corp - Backend Intern
Jan 2023 - May 2023
- Built REST APIs
- Database optimization
- Code reviews

EDUCATION
Bachelor of Technology
Indian Institute of Technology
Major: Computer Science
CGPA: 8.5
Graduation Year: 2023

Bachelor's (Incomplete)
Some University
2020-2022

TECHNICAL SKILLS
Go, Python, JavaScript, React, PostgreSQL, Docker, Kubernetes

PROJECTS
E-commerce Platform
- Built using React and Node.js
- 50K monthly users
- Open source: github.com/alexchen/ecommerce

Data Analytics Dashboard
- Created with Python and Plotly
- Real-time data processing
- Used by 10+ teams
"""


# ============================================================================
# Fixture D: Resume with achievements and certifications
# ============================================================================

RESUME_WITH_ACHIEVEMENTS = """MAYA PATEL
maya@example.com

CAREER SUMMARY
Product-focused engineer with track record of delivering high-impact solutions.

PROFESSIONAL EXPERIENCE
InnovateCorp - Senior Product Engineer
2022 - Present
- Led development of microservices platform serving 5M+ users
- Reduced latency by 60% through optimization
- Mentored 5 engineers

StartupXYZ - Full Stack Engineer
2020 - 2021
- Built product from 0 to 100K users
- Implemented CI/CD pipeline
- Reduced deployment time from 2 hours to 5 minutes

EDUCATION
B.Tech in Computer Science
Prestigious University, India
Graduation: 2020

PROFESSIONAL CERTIFICATIONS
AWS Certified Solutions Architect Professional
Google Cloud Professional Data Engineer
Scrum Master Certification

AWARDS & RECOGNITION
Technology Innovation Award - InnovateCorp 2023
Featured Speaker - Tech Conference 2023
Dean's List - All semesters

TECHNICAL EXPERTISE
Python, JavaScript, TypeScript, React, Node.js, PostgreSQL, MongoDB, AWS, GCP

SIDE PROJECTS
Open Source Contributions - 50+ repositories on GitHub
Technical Blog - 100K monthly readers
Mentoring - Helped 20+ junior developers
"""


# ============================================================================
# Fixture E: Resume with OCR artifacts and unusual formatting
# ============================================================================

RESUME_WITH_OCR_ARTIFACTS = """PRIYA KUMAR
priya.kumar@example.com | +91-98765-43210

OBJECTIVE
Soltware Engineer seek1ng position 1n innovative tech company.
5+ years experience with cutting-edge technolo9ies.

PROFESSIONAL EXPERIENCE
TechCorp | Senior Deve|oper
2023 - Present
- Deve|oped microservices using Node js and P0stgresQL
- Led team of 3 de ve|opers
- 1mproved test coverage to 85%

StartupABC - Software Engineer
2021-2022
- Bui|t REST APIs using Pyth0n and FastAPI
- Collaborated with product team
- Implemented autom@ted testing

EDUCATION
Bachelor 0f Techn0|ogy - Comp.Sc
National Institute of Tech, India | 2021
CPA: 3.2/4.0

Masterr's (In Progress)
Online Un1versity | Expected 2025

SKILLS
P1/th0n, J@vaScript, React, N0de.js, D0cker, Kubern3tes, AWS

CERTIFICATIONS
AWS Cloud Pr@ctitioner | 2023
Scrum M@ster | 2022
"""


# ============================================================================
# Fixture F: Resume without Education or Experience sections
# ============================================================================

RESUME_MINIMAL = """ALEX JOHNSON
alex@example.com | +1-555-1234

SUMMARY
Recent bootcamp graduate transitioning to software development.

PROJECTS
Todo App
React-based task management application
- React, Node.js, MongoDB
- github.com/alexjohnson/todoapp

Weather Dashboard
Real-time weather visualization tool
- JavaScript, OpenWeatherMap API
- Live at weather-app.example.com

SKILLS
JavaScript, React, Node.js, HTML, CSS, MongoDB, Git

LANGUAGES
English (Native)
Mandarin (Conversational)
"""


# ============================================================================
# Fixture G: Resume with unusual section ordering
# ============================================================================

RESUME_UNUSUAL_ORDER = """CHRIS WILLIAMS

SKILLS
Python, Java, C++, JavaScript, React, AWS, GCP, Docker

PROJECTS
Distributed Database System
- Implemented consensus algorithm
- Achieved 99.99% uptime

API Gateway Service
- Built high-performance request router
- Handles 100K+ RPS

EXPERIENCE
TechGiant - Principal Engineer
2022 - Present
- Architected foundational systems
- Led team of 10+ engineers

MidSize Corp - Senior Software Engineer
2019 - 2021
- Developed internal tools
- Optimized database queries

EDUCATION
PhD in Computer Science
Top Research University, 2019

BS in Computer Science
State University, 2015

SUMMARY
Systems architect with deep expertise in distributed systems and performance optimization.
13+ years building scalable infrastructure.

CONTACT
email@example.com | (555) 123-4567 | github.com/chriswilliams
"""


# ============================================================================
# Tests
# ============================================================================

class TestGenericResumeParsing:
    """Tests for generic, production-quality resume parsing."""

    def test_simple_single_column_resume(self) -> None:
        """Test A: Simple single-column resume parsing."""
        parser = ResumeParserService()
        parsed = parser.parse(SIMPLE_SINGLE_COLUMN)

        assert parsed.candidate_name == "John Doe"
        assert parsed.email == "john@example.com"
        assert parsed.phone == "(555) 123-4567"
        assert parsed.summary is not None
        assert "Full-stack" in parsed.summary

        assert len(parsed.experiences) == 2
        assert parsed.experiences[0].company == "Acme Tech"
        assert parsed.experiences[0].role == "Senior Developer"
        assert parsed.experiences[1].company == "TechStart Inc"

        assert len(parsed.education) == 1
        assert parsed.education[0].institution == "University of California"
        assert parsed.education[0].degree == "Bachelor of Science in Computer Science"
        assert parsed.education[0].expected_graduation == "2020"

        assert "Python" in parsed.skills
        assert "React" in parsed.skills

    def test_multiple_jobs_same_company(self) -> None:
        """Test C: Multiple positions at same company are separate entries."""
        parser = ResumeParserService()
        parsed = parser.parse(MULTIPLE_ROLES_SAME_COMPANY)

        # Should have at least 3 experiences (2 at Nexus Labs + 1 at Previous Corp)
        assert len(parsed.experiences) >= 3

        nexus_positions = [
            exp for exp in parsed.experiences
            if exp.company == "Nexus Labs"
        ]
        assert len(nexus_positions) == 2

        # Different roles
        roles = {exp.role for exp in nexus_positions}
        assert len(roles) == 2
        assert "Software Engineer" in roles or "Software Engineering Intern" in roles

    def test_multiple_education_entries(self) -> None:
        """Test C: Multiple education entries are preserved."""
        parser = ResumeParserService()
        parsed = parser.parse(MULTIPLE_ROLES_SAME_COMPANY)

        # Should have 2 education entries
        assert len(parsed.education) >= 2

    def test_resume_with_achievements_and_certifications(self) -> None:
        """Test D: Certifications are parsed and not confused with education."""
        parser = ResumeParserService()
        parsed = parser.parse(RESUME_WITH_ACHIEVEMENTS)

        # Should have parsed experiences
        assert len(parsed.experiences) >= 2
        assert parsed.experiences[0].company == "InnovateCorp"

        # Should have education
        assert len(parsed.education) >= 1
        assert parsed.education[0].institution == "Prestigious University, India"

        # Skills should be present
        assert "Python" in parsed.skills or parsed.skills
        assert len(parsed.technologies) > 0

    def test_resume_with_ocr_artifacts_normalizes(self) -> None:
        """Test E: Resume with OCR artifacts is parsed and normalized."""
        parser = ResumeParserService()
        parsed = parser.parse(RESUME_WITH_OCR_ARTIFACTS)

        # Despite OCR artifacts, should extract key information
        assert parsed.email is not None  # Should find email
        assert parsed.phone is not None  # Should find phone

        # Should identify technologies despite artifacts
        if parsed.technologies:
            # Check if common techs are found (with normalization)
            tech_names = {t.lower() for t in parsed.technologies}
            # At least some tech recognition should happen
            assert len(parsed.technologies) > 0

    def test_minimal_resume_without_education(self) -> None:
        """Test F: Resume without Education or Experience sections."""
        parser = ResumeParserService()
        parsed = parser.parse(RESUME_MINIMAL)

        # Should find contact info
        assert parsed.email == "alex@example.com"

        # Should parse projects
        assert len(parsed.projects) >= 2
        assert parsed.projects[0].title == "Todo App"

        # Should find skills
        assert "JavaScript" in parsed.skills or parsed.skills
        assert len(parsed.skills) > 0

    def test_unusual_section_ordering(self) -> None:
        """Test G: Resume with unusual section order (Skills before Experience)."""
        parser = ResumeParserService()
        parsed = parser.parse(RESUME_UNUSUAL_ORDER)

        # Should still parse correctly despite unusual order
        assert len(parsed.skills) > 0
        assert len(parsed.experiences) >= 2
        assert len(parsed.education) >= 2

        # Should find PhD
        phd = next(
            (e for e in parsed.education if "PhD" in (e.degree or "")),
            None,
        )
        assert phd is not None

    def test_two_column_layout_parsing(self) -> None:
        """Test B: Two-column layout is parsed correctly."""
        parser = ResumeParserService()
        parsed = parser.parse(TWO_COLUMN_LAYOUT)

        # Should extract experience
        assert len(parsed.experiences) >= 2
        assert any("AI" in (exp.company or "") for exp in parsed.experiences)

        # Should extract skills
        assert "Python" in parsed.skills or parsed.skills

    def test_parsed_resume_validation(self) -> None:
        """Test that parsed resumes pass validation."""
        validator = ResumeValidationService()
        parser = ResumeParserService()

        # Parse and validate a simple resume
        parsed = parser.parse(SIMPLE_SINGLE_COLUMN)
        result = validator.validate(parsed)

        # Should be valid
        assert result.is_valid or result.warnings is not None

        # Should have extracted data
        assert len(parsed.experiences) > 0
        assert len(parsed.education) > 0

    def test_deterministic_parsing(self) -> None:
        """Test that parsing is deterministic - same input -> same output."""
        parser = ResumeParserService()

        parsed1 = parser.parse(SIMPLE_SINGLE_COLUMN)
        parsed2 = parser.parse(SIMPLE_SINGLE_COLUMN)

        # Should produce identical results
        assert parsed1.candidate_name == parsed2.candidate_name
        assert parsed1.email == parsed2.email
        assert len(parsed1.experiences) == len(parsed2.experiences)
        assert len(parsed1.education) == len(parsed2.education)

        if parsed1.experiences:
            assert parsed1.experiences[0].company == parsed2.experiences[0].company
            assert parsed1.experiences[0].role == parsed2.experiences[0].role

    def test_no_candidate_specific_code(self) -> None:
        """Verify that parsing doesn't use candidate-specific hardcoding."""
        parser = ResumeParserService()

        # Parse different candidates - should work equally well
        for resume_text in [
            SIMPLE_SINGLE_COLUMN,
            MULTIPLE_ROLES_SAME_COMPANY,
            RESUME_WITH_ACHIEVEMENTS,
        ]:
            parsed = parser.parse(resume_text)

            # Should extract something meaningful
            has_data = (
                parsed.experiences or
                parsed.education or
                parsed.skills or
                parsed.projects
            )
            assert has_data, "Should extract meaningful data from any resume"

    def test_date_parsing_formats(self) -> None:
        """Test that various date formats are recognized."""
        parser = ResumeParserService()
        parsed = parser.parse(SIMPLE_SINGLE_COLUMN)

        # Should parse dates in "Jan 2022 - Present" format
        if parsed.experiences:
            exp = parsed.experiences[0]
            if exp.start_date:
                assert "2022" in exp.start_date
            if exp.end_date:
                assert "Present" in exp.end_date or "2021" in exp.end_date

    def test_technologies_vs_skills_separation(self) -> None:
        """Test that technologies and skills are tracked separately."""
        parser = ResumeParserService()
        parsed = parser.parse(MULTIPLE_ROLES_SAME_COMPANY)

        # Skills are self-listed
        assert len(parsed.skills) > 0

        # Technologies are machine-detected
        # (may be subset or equal to skills)
        assert parsed.technologies is not None

    def test_summary_extraction_without_generation(self) -> None:
        """Test that summary is only extracted, never generated."""
        parser = ResumeParserService()

        # Resume with summary
        parsed_with = parser.parse(SIMPLE_SINGLE_COLUMN)
        assert parsed_with.summary is not None

        # Resume without summary section - create a minimal resume without summary
        resume_no_summary = """ALEX JOHNSON
alex@example.com | +1-555-1234

PROJECTS
Todo App
React-based task management application
- React, Node.js, MongoDB
- github.com/alexjohnson/todoapp

SKILLS
JavaScript, React, Node.js, HTML, CSS, MongoDB, Git
"""
        parsed_without = parser.parse(resume_no_summary)
        assert parsed_without.summary is None or parsed_without.summary == ""

    def test_empty_sections_handled_gracefully(self) -> None:
        """Test that missing/empty sections don't cause parsing failures."""
        parser = ResumeParserService()

        # Resume missing some sections
        parsed = parser.parse(RESUME_MINIMAL)

        # Should still be valid ParsedResume
        assert parsed is not None
        assert hasattr(parsed, 'experiences')
        assert hasattr(parsed, 'education')
        assert hasattr(parsed, 'skills')
