from datetime import datetime

import pytest

from app.services.query_parser import QueryParser
from app.utils.experience_calc import calculate_experience_years, parse_experience_date


@pytest.fixture
def parser() -> QueryParser:
    return QueryParser()


def test_parse_python_with_experience(parser: QueryParser) -> None:
    result = parser.parse("Python developers with at least 3 years experience")

    assert "python" in result.skills
    assert result.min_experience_years == 3.0


def test_parse_backend_with_plus_experience(parser: QueryParser) -> None:
    result = parser.parse("Backend developers with 2+ years of experience")

    assert result.min_experience_years == 2.0


def test_parse_fastapi_developers(parser: QueryParser) -> None:
    result = parser.parse("FastAPI developers")

    assert "fastapi" in result.skills


def test_parse_python_and_postgresql(parser: QueryParser) -> None:
    result = parser.parse("Python developers who know PostgreSQL")

    assert "python" in result.skills
    assert "postgresql" in result.technologies


def test_parse_mongodb_and_nodejs(parser: QueryParser) -> None:
    result = parser.parse("Candidates with MongoDB and Node.js")

    assert "mongodb" in result.technologies
    assert "node.js" in result.technologies


def test_parse_task_management_projects(parser: QueryParser) -> None:
    result = parser.parse(
        "Candidates who worked on task management projects",
    )

    assert "task management" in result.projects


def test_parse_experience_date_present() -> None:
    parsed = parse_experience_date("Present")
    assert parsed is not None
    assert parsed.year == datetime.utcnow().year


def test_parse_experience_date_month_year() -> None:
    parsed = parse_experience_date("Jan 2024")
    assert parsed == datetime(2024, 1, 1)


def test_calculate_experience_single_job() -> None:
    years = calculate_experience_years(
        [
            {
                "company": "TechNova",
                "start_date": "Jan 2024",
                "end_date": "Present",
            }
        ],
    )

    assert years >= 1.5


def test_calculate_experience_multiple_jobs() -> None:
    years = calculate_experience_years(
        [
            {
                "company": "A",
                "start_date": "Jan 2020",
                "end_date": "Dec 2021",
            },
            {
                "company": "B",
                "start_date": "Jan 2022",
                "end_date": "Dec 2023",
            },
        ],
    )

    assert 3.9 <= years <= 4.1


def test_calculate_experience_overlapping_jobs_not_double_counted() -> None:
    years = calculate_experience_years(
        [
            {
                "company": "A",
                "start_date": "Jan 2020",
                "end_date": "Dec 2022",
            },
            {
                "company": "B",
                "start_date": "Jan 2021",
                "end_date": "Dec 2023",
            },
        ],
    )

    assert 3.9 <= years <= 4.1


def test_calculate_experience_missing_dates_do_not_crash() -> None:
    years = calculate_experience_years(
        [
            {"company": "A", "start_date": None, "end_date": None},
            {
                "company": "B",
                "start_date": "Jan 2023",
                "end_date": "Dec 2023",
            },
        ],
    )

    assert 0.9 <= years <= 1.1


def test_calculate_experience_no_experience_returns_zero() -> None:
    assert calculate_experience_years([]) == 0.0


def test_parse_backend_developer_role(parser: QueryParser) -> None:
    result = parser.parse("Backend developers with at least 3 years experience")

    assert result.role == "backend developer"
    assert result.min_experience_years == 3.0


def test_parse_frontend_engineer_role(parser: QueryParser) -> None:
    result = parser.parse("Frontend engineer with React experience")

    assert result.role == "frontend developer"
    assert "react" in result.skills


def test_parse_full_stack_with_skill_and_experience(parser: QueryParser) -> None:
    result = parser.parse("Full stack developer with 5+ years Python experience")

    assert result.role == "full stack developer"
    assert result.min_experience_years == 5.0
    assert "python" in result.skills


def test_parse_data_scientist_role(parser: QueryParser) -> None:
    result = parser.parse("Data scientist with machine learning experience")

    assert result.role == "data scientist"


def test_parse_devops_engineer_role(parser: QueryParser) -> None:
    result = parser.parse("DevOps engineer with Docker and Git")

    assert result.role == "devops engineer"
    assert "docker" in result.technologies


def test_parse_software_developer_role(parser: QueryParser) -> None:
    result = parser.parse("Software engineer with Java experience")

    assert result.role == "software developer"
    assert "java" in result.skills
