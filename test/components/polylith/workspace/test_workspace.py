import tempfile
from pathlib import Path
import time

import pytest
import tomlkit
from polylith.workspace.create import create_workspace, detect_workspace_state, WorkspaceStateEnum


def test_detect_workspace_state_fresh_directory():
    """Test workspace state detection on fresh directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        state = detect_workspace_state(workspace_path)

        assert state == WorkspaceStateEnum.FRESH


def test_detect_workspace_state_existing_complete_workspace():
    """Test workspace state detection on complete existing workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing workspace structure
        (workspace_path / "bases").mkdir()
        (workspace_path / "components").mkdir()
        (workspace_path / "projects").mkdir()
        (workspace_path / "workspace.toml").touch()

        # Create complete pyproject.toml
        pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"

[tool.hatch.build]
dev-mode-dirs = ["components", "bases", "development", "."]
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        state = detect_workspace_state(workspace_path)

        assert state == WorkspaceStateEnum.EXISTING_COMPLETE


def test_detect_workspace_state_existing_no_pyproject():
    """Test workspace state detection on existing workspace without pyproject.toml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing workspace structure without pyproject.toml
        (workspace_path / "bases").mkdir()
        (workspace_path / "components").mkdir()
        (workspace_path / "projects").mkdir()
        (workspace_path / "workspace.toml").touch()

        state = detect_workspace_state(workspace_path)

        assert state == WorkspaceStateEnum.EXISTING_NO_PYPROJECT


def test_detect_workspace_state_existing_incomplete_pyproject():
    """Test workspace state detection on existing workspace with incomplete pyproject.toml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing workspace structure
        (workspace_path / "bases").mkdir()
        (workspace_path / "components").mkdir()
        (workspace_path / "projects").mkdir()
        (workspace_path / "workspace.toml").touch()

        # Create incomplete pyproject.toml (missing backend config)
        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        state = detect_workspace_state(workspace_path)

        assert state == WorkspaceStateEnum.EXISTING_INCOMPLETE


def test_create_workspace_on_existing_workspace_is_noop(enforce_noninteractive):
    """Test that create_workspace on existing complete workspace doesn't modify files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create initial workspace
        create_workspace(workspace_path, "test_namespace", "loose")

        # Record initial state
        initial_files = list(workspace_path.rglob("*"))
        initial_workspace_content = (workspace_path / "workspace.toml").read_text()

        # Call create_workspace again
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify no changes
        final_files = list(workspace_path.rglob("*"))
        final_workspace_content = (workspace_path / "workspace.toml").read_text()

        assert len(initial_files) == len(final_files)
        assert initial_workspace_content == final_workspace_content


def test_create_workspace_preserves_existing_files(enforce_noninteractive):
    """Test that existing files are not modified, overwritten, or deleted."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create directory with some custom content
        (workspace_path / "bases").mkdir()
        custom_file = workspace_path / "bases" / "custom_file.py"
        custom_content = "# Custom user content\nprint('hello')"
        custom_file.write_text(custom_content)

        # Create partial workspace structure with custom workspace.toml
        custom_workspace_content = """
[tool.polylith]
namespace = "custom_namespace"
git_tag_pattern = "custom-*"

[tool.polylith.structure]
theme = "custom"
"""
        (workspace_path / "workspace.toml").write_text(custom_workspace_content)

        # Record timestamps and content before operation
        custom_file_mtime = custom_file.stat().st_mtime
        workspace_file_mtime = (workspace_path / "workspace.toml").stat().st_mtime

        # Small delay to ensure timestamps would differ if files were modified
        time.sleep(0.01)

        # Create workspace (should only add missing parts)
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify custom file is untouched
        assert custom_file.exists()
        assert custom_file.read_text() == custom_content
        assert custom_file.stat().st_mtime == custom_file_mtime

        # Verify workspace.toml is untouched (already existed)
        assert (workspace_path / "workspace.toml").read_text() == custom_workspace_content
        assert (workspace_path / "workspace.toml").stat().st_mtime == workspace_file_mtime

        # Verify missing directories were created
        assert (workspace_path / "components").exists()
        assert (workspace_path / "projects").exists()
        assert (workspace_path / "development").exists()


def test_create_workspace_with_conflicting_backend_config(enforce_noninteractive):
    """Test handling of conflicting backend in existing pyproject.toml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create workspace with existing poetry backend
        create_workspace(workspace_path, "test_namespace", "loose")

        pyproject_content = """
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "test-project"
version = "0.1.0"
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        # Attempt to create workspace with conflicting uv package manager
        with pytest.raises(ValueError, match="Conflicting backend configuration"):
            create_workspace(workspace_path, "test_namespace", "loose", package_manager="uv")