from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints.resumes import process_resume
from app.services.resume_parser_service import ResumeParserService


RESUME_TEXT = """PROFESSIONAL SUMMARY
Full stack developer building reliable web applications.

INTERNSHIP EXPERIENCE
QUMIQ \u2014 Full Stack Developer Intern Duration: 1 Month
- Worked primarily on backend development and API integration.
- Assisted in backend logic implementation and database connectivity.
BELSTACK \u2014 MERN Stack Developer Intern Duration: 1 Month
- Developed full-stack web applications using MongoDB, Express.js, React.js, and Node.js.
- Worked on frontend-backend integration and REST API handling.

EDUCATION
Bachelor of Technology (B.Tech)
Artificial Intelligence and Data Science
Excel College of Engineering, Kerala
Expected Graduation: 2027
CGPA: 7.5
"""


def test_parser_separates_multiple_duration_only_internships() -> None:
    parsed = ResumeParserService().parse(RESUME_TEXT)

    assert [(item.company, item.role, item.duration) for item in parsed.experiences] == [
        ("QUMIQ", "Full Stack Developer Intern", "1 Month"),
        ("BELSTACK", "MERN Stack Developer Intern", "1 Month"),
    ]
    assert "BELSTACK" not in parsed.experiences[0].description
    assert "QUMIQ" not in parsed.experiences[1].description
    assert parsed.experiences[0].start_date is None
    assert parsed.experiences[0].end_date is None


def test_parser_extracts_one_structured_education_record() -> None:
    education = ResumeParserService().parse(RESUME_TEXT).education

    assert len(education) == 1
    assert education[0].degree == "Bachelor of Technology (B.Tech)"
    assert education[0].field_of_study == "Artificial Intelligence and Data Science"
    assert education[0].institution == "Excel College of Engineering, Kerala"
    assert education[0].expected_graduation == "2027"
    assert education[0].cgpa == "7.5"
    assert "mented database" not in education[0].raw_text


def test_parser_keeps_education_inside_education_section() -> None:
    text = RESUME_TEXT + "\nSKILLS\nPython\n"

    parsed = ResumeParserService().parse(text)

    assert len(parsed.education) == 1
    assert all("Worked" not in item.raw_text for item in parsed.education)
    assert all("BELSTACK" not in item.raw_text for item in parsed.education)


def test_parser_extracts_professional_summary_section() -> None:
    parsed = ResumeParserService().parse(RESUME_TEXT)

    assert parsed.summary == "Full stack developer building reliable web applications."


def test_parser_handles_normal_employment_history() -> None:
    text = """PROFILE
Backend engineer focused on APIs.

EMPLOYMENT HISTORY
Northwind Labs
Senior Backend Engineer
Jan 2022 - Present
- Built service integrations.

Contoso Systems - Software Developer
Mar 2020 - Dec 2021
- Delivered internal tools.

SKILLS
Python, FastAPI
"""

    experiences = ResumeParserService().parse(text).experiences

    assert len(experiences) == 2
    assert experiences[0].company == "Northwind Labs"
    assert experiences[0].role == "Senior Backend Engineer"
    assert experiences[0].start_date == "Jan 2022"
    assert experiences[0].end_date == "Present"
    assert experiences[1].company == "Contoso Systems"
    assert experiences[1].role == "Software Developer"


def test_parser_stops_education_at_adjacent_certifications_heading() -> None:
    text = """ACADEMIC BACKGROUND
Bachelor of Science
Computer Science
Example University

CERTIFICATIONS
AWS Certified Cloud Practitioner

ACHIEVEMENTS
Dean's List
"""

    parsed = ResumeParserService().parse(text)

    assert len(parsed.education) == 1
    assert parsed.education[0].institution == "Example University"
    assert "AWS" not in parsed.education[0].raw_text
    assert "Dean" not in parsed.education[0].raw_text


def test_parser_handles_missing_summary_and_normalizes_technology_ocr() -> None:
    text = """WORK EXPERIENCE
Example Co - React,js Developer
- Used Node js and loT devices.

TECHNICAL SKILLS
React,js, Node js, Al
"""

    parsed = ResumeParserService().parse(text)

    assert parsed.summary is None
    assert "React" in parsed.technologies
    assert "Node.js" in parsed.technologies
    assert "IoT" in parsed.technologies
    assert "AI" in parsed.technologies


@pytest.mark.asyncio
async def test_process_resume_persists_parsed_summary() -> None:
    pdf_service = AsyncMock()
    pdf_service.extract_text.return_value = RESUME_TEXT
    skill_service = AsyncMock()
    skill_service.extract_skills.return_value = []
    project_service = AsyncMock()
    project_service.extract_projects.return_value = []
    education_service = AsyncMock()
    technology_service = AsyncMock()
    technology_service.extract_technologies.return_value = []
    candidate_service = AsyncMock()
    graph_service = AsyncMock()

    result = await process_resume(
        "candidate-1",
        "resume.pdf",
        pdf_service,
        skill_service,
        project_service,
        education_service,
        technology_service,
        candidate_service,
        graph_service,
    )

    assert result.experiences[0]["duration"] == "1 Month"
    assert result.education == ["Excel College of Engineering, Kerala"]
    candidate_service.update.assert_awaited_once()
    update_payload = candidate_service.update.await_args.args[1]
    assert update_payload.summary == "Full stack developer building reliable web applications."