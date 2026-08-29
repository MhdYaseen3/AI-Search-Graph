from app.schemas.search import SearchQuery
from app.services.ranking import RankingService


def test_ranking_includes_experience_weight() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Python developers with 3 years experience",
        skills=["python"],
        min_experience_years=3.0,
    )

    high_exp = {
        "candidate_id": "1",
        "full_name": "High Exp",
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 5.0,
        "summary": "Python backend developer",
    }
    low_exp = {
        "candidate_id": "2",
        "full_name": "Low Exp",
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 3.1,
        "summary": "Python developer",
    }

    ranked = service.rank([low_exp, high_exp], query)

    assert ranked[0].full_name == "High Exp"
    assert ranked[0].experience_years == 5.0
    assert ranked[0].score >= ranked[1].score


def test_ranking_skill_only_query() -> None:
    service = RankingService()
    query = SearchQuery(query="FastAPI developers", skills=["fastapi"])

    full_match = {
        "candidate_id": "1",
        "full_name": "Match",
        "matched_skills": ["fastapi"],
        "matched_technologies": [],
        "matched_projects": [],
        "skills": ["FastAPI", "Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 1.0,
        "summary": "FastAPI specialist",
    }

    ranked = service.rank([full_match], query)

    assert ranked[0].score > 0
    assert ranked[0].matched_skills == ["fastapi"]
