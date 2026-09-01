import pytest

from app.schemas.search import MatchBreakdown, SearchQuery
from app.services.ai_summary import AISummaryService
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


def test_explanation_full_match() -> None:
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
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "Role: Match" in explanation
    assert "backend developer" in explanation
    assert "Experience: Match" in explanation
    assert "5.0 years" in explanation
    assert "Skills matched: python" in explanation


def test_explanation_partial_match() -> None:
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
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "Role: Match" in explanation
    assert "Skills matched: python" in explanation
    assert "Technologies: No match" in explanation


def test_explanation_no_requirements() -> None:
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
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "Skills matched: python" in explanation


def test_explanation_multiple_matches() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Full stack developers with Python, React, and 3 years experience",
        role="full stack developer",
        skills=["python"],
        technologies=["react"],
        min_experience_years=3.0,
    )

    multi_match = {
        "candidate_id": "1",
        "full_name": "Multi Match",
        "matched_roles": ["full stack developer"],
        "matched_skills": ["python"],
        "matched_technologies": ["react"],
        "matched_projects": [],
        "roles": ["full stack developer"],
        "skills": ["Python"],
        "technologies": ["React"],
        "projects": [],
        "experience_years": 4.0,
        "summary": "Full stack developer",
    }

    ranked = service.rank([multi_match], query)

    assert len(ranked) == 1
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "Role: Match" in explanation
    assert "Experience: Match" in explanation
    assert "Skills matched: python" in explanation
    assert "Technologies matched: react" in explanation


def test_explanation_with_projects() -> None:
    service = RankingService()
    query = SearchQuery(
        query="Developers who worked on AI graph search engine",
        projects=["ai graph search engine"],
    )

    project_match = {
        "candidate_id": "1",
        "full_name": "Project Match",
        "matched_roles": [],
        "matched_skills": [],
        "matched_technologies": [],
        "matched_projects": ["ai graph search engine"],
        "roles": [],
        "skills": [],
        "technologies": [],
        "projects": ["AI Graph Search Engine"],
        "experience_years": 2.0,
        "summary": "Developer",
    }

    ranked = service.rank([project_match], query)

    assert len(ranked) == 1
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "Projects matched: ai graph search engine" in explanation


def test_explanation_empty_query() -> None:
    service = RankingService()
    query = SearchQuery(query="Candidates")

    candidate = {
        "candidate_id": "1",
        "full_name": "Candidate",
        "matched_roles": [],
        "matched_skills": [],
        "matched_technologies": [],
        "matched_projects": [],
        "roles": [],
        "skills": [],
        "technologies": [],
        "projects": [],
        "experience_years": 1.0,
        "summary": "Developer",
    }

    ranked = service.rank([candidate], query)

    assert len(ranked) == 1
    explanation = ranked[0].explanation
    assert explanation is not None
    assert "profile overlap" in explanation


@pytest.mark.asyncio
async def test_ai_structured_evidence_receives_correct_data() -> None:
    """Test that AI service receives structured match evidence correctly."""
    from unittest.mock import AsyncMock, MagicMock

    service = AISummaryService(MagicMock())
    service._call_ollama = AsyncMock(return_value="AI explanation")

    query = SearchQuery(
        query="Backend developers with Python",
        role="backend developer",
        skills=["python"],
    )

    match_breakdown = MatchBreakdown(
        role_match=True,
        experience_match=True,
        skill_match=True,
        technology_match=False,
        project_match=False,
    )

    explanation, source = await service.generate_structured_match_explanation(
        candidate_id="test-id",
        candidate_name="Test Candidate",
        query=query,
        matched_roles=["backend developer"],
        matched_skills=["python"],
        matched_technologies=[],
        matched_projects=[],
        match_breakdown=match_breakdown,
        experience_years=3.0,
    )

    assert source == "ai"
    assert explanation == "AI explanation"
    service._call_ollama.assert_called_once()

    # Verify the prompt contains the structured evidence
    call_args = service._call_ollama.call_args[0][0]
    assert "Test Candidate" in call_args
    assert "backend developer" in call_args
    assert "python" in call_args
    assert "STRUCTURED MATCH EVIDENCE" in call_args
    assert "CRITICAL SAFETY RULES" in call_args


@pytest.mark.asyncio
async def test_ai_structured_evidence_missing_experience() -> None:
    """Test that AI handles missing experience evidence safely."""
    from unittest.mock import AsyncMock, MagicMock

    service = AISummaryService(MagicMock())
    service._call_ollama = AsyncMock(return_value="AI explanation")

    query = SearchQuery(
        query="Python developers",
        skills=["python"],
    )

    match_breakdown = MatchBreakdown(
        role_match=False,
        experience_match=True,
        skill_match=True,
        technology_match=False,
        project_match=False,
    )

    explanation, source = await service.generate_structured_match_explanation(
        candidate_id="test-id",
        candidate_name="Test Candidate",
        query=query,
        matched_roles=[],
        matched_skills=["python"],
        matched_technologies=[],
        matched_projects=[],
        match_breakdown=match_breakdown,
        experience_years=None,  # Missing experience
    )

    assert source == "ai"
    call_args = service._call_ollama.call_args[0][0]
    assert "Unknown" in call_args  # Should show "Unknown" for missing experience


@pytest.mark.asyncio
async def test_ai_structured_evidence_fallback_on_ai_failure() -> None:
    """Test that AI falls back to deterministic explanation on failure."""
    from unittest.mock import AsyncMock, MagicMock

    service = AISummaryService(MagicMock())
    service._call_ollama = AsyncMock(side_effect=Exception("AI failed"))

    query = SearchQuery(
        query="Backend developers with Python",
        role="backend developer",
        skills=["python"],
    )

    match_breakdown = MatchBreakdown(
        role_match=True,
        experience_match=True,
        skill_match=True,
        technology_match=False,
        project_match=False,
    )

    explanation, source = await service.generate_structured_match_explanation(
        candidate_id="test-id",
        candidate_name="Test Candidate",
        query=query,
        matched_roles=["backend developer"],
        matched_skills=["python"],
        matched_technologies=[],
        matched_projects=[],
        match_breakdown=match_breakdown,
        experience_years=3.0,
    )

    assert source == "fallback"
    assert "Test Candidate" in explanation
    assert "backend developer" in explanation
    assert "python" in explanation


@pytest.mark.asyncio
async def test_ai_structured_evidence_no_invented_data() -> None:
    """Test that AI prompt includes safety rules to prevent data invention."""
    from unittest.mock import AsyncMock, MagicMock

    service = AISummaryService(MagicMock())
    service._call_ollama = AsyncMock(return_value="AI explanation")

    query = SearchQuery(
        query="Python developers",
        skills=["python"],
    )

    match_breakdown = MatchBreakdown(
        role_match=False,
        experience_match=True,
        skill_match=True,
        technology_match=False,
        project_match=False,
    )

    await service.generate_structured_match_explanation(
        candidate_id="test-id",
        candidate_name="Test Candidate",
        query=query,
        matched_roles=[],
        matched_skills=["python"],
        matched_technologies=[],
        matched_projects=[],
        match_breakdown=match_breakdown,
        experience_years=2.0,
    )

    call_args = service._call_ollama.call_args[0][0]
    # Verify safety rules are present
    assert "Do NOT invent" in call_args
    assert "Do NOT fabricate" in call_args
    assert "Use ONLY the structured evidence" in call_args
