"""Tests for candidate comparison service."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import NotFoundError, ValidationError
from app.db.neo4j import Neo4jConnection
from app.schemas.comparison import ComparisonRequest, ComparisonResult
from app.services.ai_summary import AISummaryService
from app.services.candidate_comparison import CandidateComparisonService


@pytest.fixture
def mock_neo4j() -> AsyncMock:
    """Mock Neo4j connection."""
    mock = AsyncMock(spec=Neo4jConnection)
    return mock


@pytest.fixture
def mock_ai_summary() -> AsyncMock:
    """Mock AI summary service."""
    mock = AsyncMock(spec=AISummaryService)
    return mock


@pytest.fixture
def sample_candidate_data() -> dict:
    """Sample candidate data from Neo4j."""
    return {
        "candidate_id": "cand-1",
        "full_name": "John Doe",
        "email": "john@example.com",
        "summary": "Software engineer with 5 years experience",
        "skills": ["Python", "JavaScript", "React", "PostgreSQL"],
        "technologies": ["Docker", "AWS", "Git"],
        "projects": ["Project A", "Project B"],
        "education": ["University A", "University B"],
        "experiences": [
            {
                "company": "Tech Corp",
                "role": "Senior Developer",
                "start_date": "2020-01-01",
                "end_date": "2023-01-01",
            }
        ],
    }


@pytest.mark.asyncio
async def test_compare_candidates_validates_request(mock_neo4j: AsyncMock, mock_ai_summary: AsyncMock) -> None:
    """Test that comparison request validation works."""
    from pydantic import ValidationError as PydanticValidationError

    # Test minimum candidates - Pydantic validates before service
    with pytest.raises(PydanticValidationError):
        ComparisonRequest(candidate_ids=["cand-1"])

    # Test maximum candidates - Pydantic validates before service
    with pytest.raises(PydanticValidationError):
        ComparisonRequest(candidate_ids=["cand-1", "cand-2", "cand-3", "cand-4"])


@pytest.mark.asyncio
async def test_compare_candidates_fetches_actual_data(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that comparison fetches actual candidate data from Neo4j."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    # Mock Neo4j response - wrap in list for each candidate
    mock_neo4j.execute_read.side_effect = [[sample_candidate_data], [sample_candidate_data]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify Neo4j was called with correct query
    assert mock_neo4j.execute_read.call_count == 2

    # Verify candidate data is from actual response
    assert len(result.candidates) == 2
    assert result.candidates[0].full_name == "John Doe"
    assert result.candidates[0].skills == ["Python", "JavaScript", "React", "PostgreSQL"]


@pytest.mark.asyncio
async def test_compare_candidates_handles_missing_candidate(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
) -> None:
    """Test that missing candidates are handled gracefully."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    # Mock Neo4j to return empty for one candidate
    mock_neo4j.execute_read.side_effect = [[], []]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Should return error instead of crash
    assert result.error is not None
    assert "not found" in result.error.lower()


@pytest.mark.asyncio
async def test_compare_candidates_calculates_metrics(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
) -> None:
    """Test that objective comparison metrics are calculated correctly."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    # Mock two candidates with different skills
    candidate_a = {
        "candidate_id": "cand-1",
        "full_name": "Alice",
        "email": "alice@example.com",
        "summary": None,
        "skills": ["Python", "JavaScript", "React"],
        "technologies": ["Docker", "AWS"],
        "projects": ["Project A"],
        "education": ["University A"],
        "experiences": [],
    }

    candidate_b = {
        "candidate_id": "cand-2",
        "full_name": "Bob",
        "email": "bob@example.com",
        "summary": None,
        "skills": ["Python", "Java", "Go"],
        "technologies": ["Docker", "Kubernetes"],
        "projects": ["Project B"],
        "education": ["University B"],
        "experiences": [],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify metrics were calculated
    assert len(result.metrics) > 0
    metric_key = "cand-1_vs_cand-2"
    assert metric_key in result.metrics

    # Verify skill overlap calculation (Python is shared)
    # Skills: A={Python, JavaScript, React}, B={Python, Java, Go}
    # Shared: {Python}, All: {Python, JavaScript, React, Java, Go}
    # Overlap: 1/5 = 20%
    assert result.metrics[metric_key].skill_overlap == 20


@pytest.mark.asyncio
async def test_compare_candidates_uses_ai_service(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that AI service is called for comparative analysis."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    # Mock Neo4j response
    mock_neo4j.execute_read.side_effect = [[sample_candidate_data], [sample_candidate_data]]

    # Mock AI service
    mock_ai_summary._call_ollama.return_value = "Alice has stronger Python skills while Bob has more Java experience."

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify AI was called
    assert mock_ai_summary._call_ollama.called

    # Verify AI analysis is in result
    assert result.ai_analysis is not None
    assert "Alice" in result.ai_analysis or "Bob" in result.ai_analysis


@pytest.mark.asyncio
async def test_compare_candidates_handles_ai_failure(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that AI failure doesn't crash comparison."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    # Mock Neo4j response with different candidates
    candidate_a = {**sample_candidate_data, "candidate_id": "cand-1", "full_name": "Alice"}
    candidate_b = {**sample_candidate_data, "candidate_id": "cand-2", "full_name": "Bob"}
    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    # Mock AI service failure
    mock_ai_summary._call_ollama.side_effect = Exception("AI service down")

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Should still return result with fallback analysis
    assert result.ai_analysis is not None
    # Fallback analysis should contain actual candidate data
    assert "Alice" in result.ai_analysis or "Bob" in result.ai_analysis or "candidates" in result.ai_analysis.lower()


@pytest.mark.asyncio
async def test_compare_candidates_no_ai_service(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that comparison works without AI service."""
    service = CandidateComparisonService(mock_neo4j, None)

    # Mock Neo4j response
    mock_neo4j.execute_read.side_effect = [[sample_candidate_data], [sample_candidate_data]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Should still return result with fallback analysis
    assert result.ai_analysis is not None
    assert result.recommendation is not None


@pytest.mark.asyncio
async def test_compare_candidates_three_candidates(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
) -> None:
    """Test that comparison works with 3 candidates."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    candidate_a = {
        "candidate_id": "cand-1",
        "full_name": "Alice",
        "email": "alice@example.com",
        "summary": None,
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    candidate_b = {
        "candidate_id": "cand-2",
        "full_name": "Bob",
        "email": "bob@example.com",
        "summary": None,
        "skills": ["Java"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    candidate_c = {
        "candidate_id": "cand-3",
        "full_name": "Charlie",
        "email": "charlie@example.com",
        "summary": None,
        "skills": ["Go"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b], [candidate_c]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2", "cand-3"])
    )

    # Should have 3 candidates
    assert len(result.candidates) == 3
    assert result.candidates[0].full_name == "Alice"
    assert result.candidates[1].full_name == "Bob"
    assert result.candidates[2].full_name == "Charlie"


@pytest.mark.asyncio
async def test_comparison_fallback_uses_actual_names(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that fallback comparison uses actual candidate names, not mock data."""
    service = CandidateComparisonService(mock_neo4j, None)

    # Mock Neo4j response with actual names
    candidate_a = {
        **sample_candidate_data,
        "candidate_id": "cand-1",
        "full_name": "Alexander Mathew",
    }

    candidate_b = {
        **sample_candidate_data,
        "candidate_id": "cand-2",
        "full_name": "Mohammed Yaseen",
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify actual names are used in fallback
    assert "Alexander Mathew" in result.ai_analysis or "Mohammed Yaseen" in result.ai_analysis
    assert "Sarah Jenkins" not in result.ai_analysis


@pytest.mark.asyncio
async def test_comparison_does_not_use_mock_percentages(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that comparison doesn't use hardcoded mock percentages."""
    service = CandidateComparisonService(mock_neo4j, None)

    candidate_a = {
        **sample_candidate_data,
        "candidate_id": "cand-1",
        "full_name": "Alexander Mathew",
        "skills": ["Python", "JavaScript"],
    }

    candidate_b = {
        **sample_candidate_data,
        "candidate_id": "cand-2",
        "full_name": "Mohammed Yaseen",
        "skills": ["Python", "Java"],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify metrics are calculated, not hardcoded
    # Skills: A={Python, JavaScript}, B={Python, Java}
    # Shared: {Python}, All: {Python, JavaScript, Java}
    # Overlap: 1/3 = 33%
    metric_key = "cand-1_vs_cand-2"
    assert result.metrics[metric_key].skill_overlap == 33

    # Verify no hardcoded 95% values
    assert "95%" not in result.ai_analysis


@pytest.mark.asyncio
async def test_ai_prompt_forbids_markdown(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
) -> None:
    """Test that AI prompt explicitly forbids markdown formatting."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    candidate_a = {
        "candidate_id": "cand-1",
        "full_name": "Alice",
        "email": "alice@example.com",
        "summary": None,
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    candidate_b = {
        "candidate_id": "cand-2",
        "full_name": "Bob",
        "email": "bob@example.com",
        "summary": None,
        "skills": ["Java"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    # Capture the prompt sent to AI
    prompt_captured = []
    def capture_prompt(prompt: str) -> str:
        prompt_captured.append(prompt)
        return "Alice has Python skills while Bob has Java skills."

    mock_ai_summary._call_ollama.side_effect = capture_prompt

    await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify prompt contains instruction to avoid markdown
    assert len(prompt_captured) > 0
    prompt_text = prompt_captured[0]
    assert "plain text" in prompt_text.lower() or "without markdown" in prompt_text.lower()
    assert "asterisks" in prompt_text.lower() or "special characters" in prompt_text.lower()


@pytest.mark.asyncio
async def test_candidate_names_never_exposed_as_uuids(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that candidate names are never exposed as UUIDs in the response."""
    service = CandidateComparisonService(mock_neo4j, None)

    candidate_a = {
        **sample_candidate_data,
        "candidate_id": "cand-1",
        "full_name": "Alexander Mathew",
    }

    candidate_b = {
        **sample_candidate_data,
        "candidate_id": "cand-2",
        "full_name": "Mohammed Yaseen",
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify actual names are in response
    assert "Alexander Mathew" in result.ai_analysis or "Mohammed Yaseen" in result.ai_analysis

    # Verify UUIDs are NOT in response
    assert "cand-1" not in result.ai_analysis
    assert "cand-2" not in result.ai_analysis
    assert "candidate_id" not in result.ai_analysis.lower()


@pytest.mark.asyncio
async def test_unknown_experience_handled_as_not_available(
    mock_neo4j: AsyncMock,
) -> None:
    """Test that unknown experience (no experiences) is converted to None."""
    service = CandidateComparisonService(mock_neo4j, None)

    candidate_a = {
        "candidate_id": "cand-1",
        "full_name": "Alice",
        "email": "alice@example.com",
        "summary": None,
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],  # Empty experiences list
        "experience_years": None,  # Will be set by service
    }

    candidate_b = {
        "candidate_id": "cand-2",
        "full_name": "Bob",
        "email": "bob@example.com",
        "summary": None,
        "skills": ["Java"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],  # Empty experiences list
        "experience_years": None,  # Will be set by service
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify unknown experience (empty experiences) is converted to None
    assert result.candidates[0].experience_years is None
    assert result.candidates[1].experience_years is None

    # Verify fallback doesn't treat it as zero
    # (experience diff should be None when both are unknown)
    metric_key = "cand-1_vs_cand-2"
    assert result.metrics[metric_key].total_experience_diff is None


@pytest.mark.asyncio
async def test_skill_coverage_never_exceeds_100_percent(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that skill coverage metric is bounded by 100%."""
    service = CandidateComparisonService(mock_neo4j, None)

    # Candidate A has many skills
    candidate_a = {
        **sample_candidate_data,
        "candidate_id": "cand-1",
        "full_name": "Alice",
        "skills": ["Python", "JavaScript", "Java", "C++", "Go", "Rust", "TypeScript", "Swift", "Kotlin", "Ruby"],
    }

    # Candidate B has few skills, all contained in A
    candidate_b = {
        **sample_candidate_data,
        "candidate_id": "cand-2",
        "full_name": "Bob",
        "skills": ["Python", "Java"],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    metric_key = "cand-1_vs_cand-2"
    assert result.metrics[metric_key].skill_coverage <= 100
    assert result.metrics[metric_key].skill_overlap <= 100


@pytest.mark.asyncio
async def test_ai_prompt_uses_actual_names_not_numbers(
    mock_neo4j: AsyncMock,
    mock_ai_summary: AsyncMock,
) -> None:
    """Test that AI prompt uses actual candidate names, not numbered labels."""
    service = CandidateComparisonService(mock_neo4j, mock_ai_summary)

    candidate_a = {
        "candidate_id": "cand-1",
        "full_name": "Alexander Mathew",
        "email": "alex@example.com",
        "summary": None,
        "skills": ["Python"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    candidate_b = {
        "candidate_id": "cand-2",
        "full_name": "Mohammed Yaseen",
        "email": "mohammed@example.com",
        "summary": None,
        "skills": ["Java"],
        "technologies": [],
        "projects": [],
        "education": [],
        "experiences": [],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b]]

    # Capture the prompt sent to AI
    prompt_captured = []
    def capture_prompt(prompt: str) -> str:
        prompt_captured.append(prompt)
        return "Alexander Mathew has Python skills while Mohammed Yaseen has Java skills."

    mock_ai_summary._call_ollama.side_effect = capture_prompt

    await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2"])
    )

    # Verify prompt contains actual names
    assert len(prompt_captured) > 0
    prompt_text = prompt_captured[0]
    assert "Alexander Mathew" in prompt_text
    assert "Mohammed Yaseen" in prompt_text

    # Verify prompt instructs against generic labels (not checking specific text in instructions)
    # The actual candidate section should not have numbered prefixes
    assert "Alexander Mathew:\n" in prompt_text or "Alexander Mathew:" in prompt_text
    assert "Mohammed Yaseen:\n" in prompt_text or "Mohammed Yaseen:" in prompt_text


@pytest.mark.asyncio
async def test_three_candidate_comparison_uses_actual_names(
    mock_neo4j: AsyncMock,
    sample_candidate_data: dict,
) -> None:
    """Test that three-candidate comparison uses actual names in fallback."""
    service = CandidateComparisonService(mock_neo4j, None)

    candidate_a = {
        **sample_candidate_data,
        "candidate_id": "cand-1",
        "full_name": "Alexander Mathew",
        "skills": ["Python"],
    }

    candidate_b = {
        **sample_candidate_data,
        "candidate_id": "cand-2",
        "full_name": "Mohammed Yaseen",
        "skills": ["Java"],
    }

    candidate_c = {
        **sample_candidate_data,
        "candidate_id": "cand-3",
        "full_name": "Arjun Menon",
        "skills": ["JavaScript"],
    }

    mock_neo4j.execute_read.side_effect = [[candidate_a], [candidate_b], [candidate_c]]

    result = await service.compare_candidates(
        ComparisonRequest(candidate_ids=["cand-1", "cand-2", "cand-3"])
    )

    # Verify fallback uses actual names
    assert "Alexander Mathew" in result.ai_analysis
    assert "Mohammed Yaseen" in result.ai_analysis
    assert "Arjun Menon" in result.ai_analysis

    # Verify no generic labels
    assert "Candidate 1" not in result.ai_analysis
    assert "Candidate 2" not in result.ai_analysis
    assert "Candidate 3" not in result.ai_analysis
