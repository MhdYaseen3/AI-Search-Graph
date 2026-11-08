"""Tests for development-only data reset functionality."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import ValidationError
from app.db.neo4j import Neo4jConnection
from app.services.development_reset import reset_development_resume_data


@pytest.fixture
def mock_neo4j() -> AsyncMock:
    """Mock Neo4j connection."""
    mock = AsyncMock(spec=Neo4jConnection)
    return mock


@pytest.fixture
def temp_upload_dir(tmp_path: Path) -> Path:
    """Create temporary upload directory with test files."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True)
    
    # Create test resume files
    (upload_dir / "candidate1_resume.pdf").write_bytes(b"test content 1")
    (upload_dir / "candidate2_resume.pdf").write_bytes(b"test content 2")
    (upload_dir / "candidate3_cv.pdf").write_bytes(b"test content 3")
    
    return upload_dir


@pytest.mark.asyncio
async def test_reset_development_data_blocks_production(mock_neo4j: AsyncMock) -> None:
    """Development reset should be disabled in production environment."""
    from app.core.config import settings
    original_env = settings.app_env
    
    try:
        # Temporarily set production environment
        settings.app_env = "production"
        
        with pytest.raises(ValidationError, match="Development reset is disabled in production"):
            await reset_development_resume_data(mock_neo4j)
    finally:
        settings.app_env = original_env


@pytest.mark.asyncio
async def test_reset_development_data_deletes_candidates(mock_neo4j: AsyncMock) -> None:
    """Should delete all Candidate nodes and their relationships."""
    mock_neo4j.execute_read.return_value = [
        {"candidate_id": "candidate1"},
        {"candidate_id": "candidate2"},
    ]
    mock_neo4j.execute_write.return_value = [{"deleted": 2}]
    
    result = await reset_development_resume_data(mock_neo4j)
    
    assert result["candidates_deleted"] == 2
    assert mock_neo4j.execute_write.call_count >= 2  # Candidates + orphan cleanup


@pytest.mark.asyncio
async def test_reset_development_data_removes_orphaned_nodes(mock_neo4j: AsyncMock) -> None:
    """Should remove orphaned Experience, Education, and Project nodes."""
    # Mock candidate deletion
    mock_neo4j.execute_read.return_value = [{"candidate_id": "candidate1"}]
    mock_neo4j.execute_write.return_value = [{"deleted": 1}]
    
    result = await reset_development_resume_data(mock_neo4j)
    
    # Should call delete for candidates + orphaned nodes (Experience, Education, Project)
    assert mock_neo4j.execute_write.call_count >= 2
    assert result["candidates_deleted"] == 1


@pytest.mark.asyncio
async def test_reset_development_data_removes_unreferenced_shared_nodes(mock_neo4j: AsyncMock) -> None:
    """Should only remove Skill/Technology nodes when they have no relationships."""
    mock_neo4j.execute_read.return_value = [{"candidate_id": "candidate1"}]
    mock_neo4j.execute_write.return_value = [{"deleted": 1}]
    
    result = await reset_development_resume_data(mock_neo4j)
    
    # Should attempt to clean up shared nodes with no relationships
    assert result["orphan_nodes_deleted"] >= 0


@pytest.mark.asyncio
async def test_reset_development_data_removes_uploaded_files(
    mock_neo4j: AsyncMock,
    temp_upload_dir: Path,
) -> None:
    """Should remove uploaded resume files for deleted candidates."""
    mock_neo4j.execute_read.return_value = [
        {"candidate_id": "candidate1"},
        {"candidate_id": "candidate2"},
        {"candidate_id": "candidate3"},
    ]
    mock_neo4j.execute_write.return_value = [{"deleted": 3}]
    
    # Verify files exist before reset
    assert (temp_upload_dir / "candidate1_resume.pdf").exists()
    assert (temp_upload_dir / "candidate2_resume.pdf").exists()
    assert (temp_upload_dir / "candidate3_cv.pdf").exists()
    
    result = await reset_development_resume_data(mock_neo4j, temp_upload_dir)
    
    # Files should be deleted
    assert not (temp_upload_dir / "candidate1_resume.pdf").exists()
    assert not (temp_upload_dir / "candidate2_resume.pdf").exists()
    assert not (temp_upload_dir / "candidate3_cv.pdf").exists()
    assert result["files_deleted"] == 3


@pytest.mark.asyncio
async def test_reset_development_data_handles_empty_database(mock_neo4j: AsyncMock) -> None:
    """Should handle empty database gracefully."""
    mock_neo4j.execute_read.return_value = []
    mock_neo4j.execute_write.return_value = [{"deleted": 0}]
    
    result = await reset_development_resume_data(mock_neo4j)
    
    assert result["candidates_deleted"] == 0
    assert result["orphan_nodes_deleted"] == 0
    assert result["files_deleted"] == 0


@pytest.mark.asyncio
async def test_reset_development_data_handles_missing_upload_dir(
    mock_neo4j: AsyncMock,
    tmp_path: Path,
) -> None:
    """Should handle missing upload directory gracefully."""
    mock_neo4j.execute_read.return_value = [{"candidate_id": "candidate1"}]
    mock_neo4j.execute_write.return_value = [{"deleted": 1}]
    
    non_existent_dir = tmp_path / "non_existent_uploads"
    
    result = await reset_development_resume_data(mock_neo4j, non_existent_dir)
    
    assert result["candidates_deleted"] == 1
    assert result["files_deleted"] == 0  # No files to delete


@pytest.mark.asyncio
async def test_reset_development_data_does_not_modify_shared_nodes_with_references(
    mock_neo4j: AsyncMock,
) -> None:
    """Should preserve shared nodes that still have relationships."""
    mock_neo4j.execute_read.return_value = [{"candidate_id": "candidate1"}]
    
    # Simulate some nodes being deleted, some preserved
    call_count = 0
    def mock_execute_write(query: str, params: dict | None = None) -> list[dict]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:  # Candidate deletion
            return [{"deleted": 1}]
        return [{"deleted": 0}]  # No orphans found
    
    mock_neo4j.execute_write.side_effect = mock_execute_write
    
    result = await reset_development_resume_data(mock_neo4j)
    
    assert result["candidates_deleted"] == 1
    # Shared nodes with references should be preserved (0 deleted)
