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


def test_ranking_includes_role_weight() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Backend developers with Python",
        role="backend developer",
        skills=["python"],
    )

    role_match = {
        "candidate_id": "1",
        "full_name": "Backend Dev",
        "matched_roles": ["backend developer"],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["backend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 3.0,
        "summary": "Python backend developer",
    }

    ranked = service.rank([role_match], query)

    assert ranked[0].score > 0
    assert ranked[0].matched_roles == ["backend developer"]


def test_ranking_role_mismatch_lower_score() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Backend developers with Python",
        role="backend developer",
        skills=["python"],
    )

    role_mismatch = {
        "candidate_id": "1",
        "full_name": "Frontend Dev",
        "matched_roles": [],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["frontend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 3.0,
        "summary": "Python frontend developer",
    }

    ranked = service.rank([role_mismatch], query)

    # Should still rank due to skill match, but without role boost
    assert ranked[0].score > 0
    assert ranked[0].matched_roles == []


def test_ranking_role_and_skill_combined() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Python backend developers",
        role="backend developer",
        skills=["python"],
    )

    full_match = {
        "candidate_id": "1",
        "full_name": "Full Match",
        "matched_roles": ["backend developer"],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["backend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 2.0,
        "summary": "Python backend developer",
    }

    skill_only = {
        "candidate_id": "2",
        "full_name": "Skill Only",
        "matched_roles": [],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["frontend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 2.0,
        "summary": "Python frontend developer",
    }

    ranked = service.rank([skill_only, full_match], query)

    # Full match (role + skill) should rank higher than skill only
    assert ranked[0].full_name == "Full Match"
    assert ranked[0].score > ranked[1].score


def test_match_breakdown_full_match() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Backend developers with Python and 3 years experience",
        role="backend developer",
        skills=["python"],
        min_experience_years=3.0,
    )

    full_match = {
        "candidate_id": "1",
        "full_name": "Full Match",
        "matched_roles": ["backend developer"],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["backend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 5.0,
        "summary": "Python backend developer",
    }

    ranked = service.rank([full_match], query)

    assert len(ranked) == 1
    assert ranked[0].match_breakdown.role_match is True
    assert ranked[0].match_breakdown.experience_match is True
    assert ranked[0].match_breakdown.skill_match is True
    assert ranked[0].match_breakdown.technology_match is False
    assert ranked[0].match_breakdown.project_match is False


def test_match_breakdown_partial_match() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Backend developers with Python and PostgreSQL",
        role="backend developer",
        skills=["python"],
        technologies=["postgresql"],
    )

    partial_match = {
        "candidate_id": "1",
        "full_name": "Partial Match",
        "matched_roles": ["backend developer"],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["backend developer"],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 2.0,
        "summary": "Python backend developer",
    }

    ranked = service.rank([partial_match], query)

    assert len(ranked) == 1
    assert ranked[0].match_breakdown.role_match is True
    assert ranked[0].match_breakdown.experience_match is True  # No requirement
    assert ranked[0].match_breakdown.skill_match is True
    assert ranked[0].match_breakdown.technology_match is False
    assert ranked[0].match_breakdown.project_match is False


def test_match_breakdown_experience_mismatch() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Backend developers with 5 years experience",
        role="backend developer",
        min_experience_years=5.0,
    )

    sufficient_exp = {
        "candidate_id": "1",
        "full_name": "Good Experience",
        "matched_roles": ["backend developer"],
        "matched_skills": [],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": ["backend developer"],
        "skills": [],
        "technologies": [],
        "projects": [],
        "experience_years": 6.0,
        "summary": "Senior backend developer",
    }

    ranked = service.rank([sufficient_exp], query)

    assert len(ranked) == 1
    assert ranked[0].match_breakdown.role_match is True
    assert ranked[0].match_breakdown.experience_match is True
    assert ranked[0].match_breakdown.skill_match is False
    assert ranked[0].match_breakdown.technology_match is False
    assert ranked[0].match_breakdown.project_match is False


def test_match_breakdown_no_requirements() -> None:
    service = RankingService()
    query = SearchQuery(query="Python developers", skills=["python"])

    candidate = {
        "candidate_id": "1",
        "full_name": "Candidate",
        "matched_roles": [],
        "matched_skills": ["python"],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": [],
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "experience_years": 1.0,
        "summary": "Python developer",
    }

    ranked = service.rank([candidate], query)

    assert len(ranked) == 1
    assert ranked[0].match_breakdown.role_match is False
    assert ranked[0].match_breakdown.experience_match is True
    assert ranked[0].match_breakdown.skill_match is True
    assert ranked[0].match_breakdown.technology_match is False
    assert ranked[0].match_breakdown.project_match is False
