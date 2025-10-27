import tempfile
import textwrap
from pathlib import Path
from unittest.mock import Mock

import pytest
from polylith.workspace.create import (
    create_workspace,
    is_interactive_environment,
    prompt_for_pyproject_creation_and_configuration,
    display_setup_completion_message,
    PackageManagerEnum,
    detect_package_manager,
    detect_command_context,
    prompt_for_package_manager_configuration_with_detection,
)


@pytest.fixture
def mock_tty_true(monkeypatch):
    """Fixture to simulate TTY environment (interactive)."""
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)


@pytest.fixture
def mock_tty_false(monkeypatch):
    """Fixture to simulate non-TTY environment (CI/batch)."""
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)


@pytest.fixture
def mock_user_input(monkeypatch):
    """Fixture to mock user input with automatic monkeypatching."""
    mock = Mock()
    monkeypatch.setattr('builtins.input', mock)
    return mock


@pytest.fixture
def mock_interactive_functions(monkeypatch):
    """Fixture providing mocks for all interactive functions."""
    mocks = {}

    mocks['is_interactive'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.is_interactive_environment', mocks['is_interactive'])


    mocks['prompt_pyproject'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.prompt_for_pyproject_creation_and_configuration', mocks['prompt_pyproject'])

    mocks['display'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.display_setup_completion_message', mocks['display'])

    mocks['prompt_with_detection'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.prompt_for_package_manager_configuration_with_detection', mocks['prompt_with_detection'])

    return mocks


def test_is_interactive_environment_true(mock_tty_true):
    """Test interactive environment detection when TTY is available."""
    assert is_interactive_environment() is True


def test_is_interactive_environment_false(mock_tty_false):
    """Test interactive environment detection when TTY is not available."""
    assert is_interactive_environment() is False



def test_display_setup_completion_message(monkeypatch):
    """Test completion message provides clear guidance for manual setup."""
    mock_print = Mock()
    monkeypatch.setattr('builtins.print', mock_print)

    display_setup_completion_message()

    # Verify print was called
    mock_print.assert_called()

    # Get all printed messages
    call_args = [call[0][0] for call in mock_print.call_args_list]
    full_message = "\n".join(call_args)

    # Verify the complete expected message content
    expected_messages = [
        "Workspace created successfully!",
        "To complete setup, either:",
        "1. Configure pyproject.toml manually (see: https://davidvujic.github.io/python-polylith-docs/setup/)",
        "2. Re-run with: poly create workspace --package-manager uv"
    ]

    for expected in expected_messages:
        assert expected in full_message


def test_create_workspace_interactive_with_existing_pyproject(mock_interactive_functions):
    """Test workspace creation in interactive mode with existing pyproject.toml."""
    # Setup mocks
    mock_interactive_functions['is_interactive'].return_value = True
    mock_interactive_functions['prompt_with_detection'].return_value = PackageManagerEnum.UV

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing pyproject.toml
        existing_content = textwrap.dedent("""
            [project]
            name = "test-project"
            version = "0.1.0"
        """).strip()
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # Create workspace without package_manager parameter
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify behavior: should use detection-based prompting and configure backend
        mock_interactive_functions['is_interactive'].assert_called_once()
        mock_interactive_functions['prompt_with_detection'].assert_called_once()
        mock_interactive_functions['display'].assert_not_called()  # No completion message needed

        # Verify backend was configured
        content = (workspace_path / "pyproject.toml").read_text()
        assert "hatchling" in content


def test_create_workspace_interactive_no_pyproject_user_declines(mock_interactive_functions):
    """Test workspace creation when user declines to configure package manager."""
    # Setup mocks
    mock_interactive_functions['is_interactive'].return_value = True
    mock_interactive_functions['prompt_pyproject'].return_value = None  # User declines

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create workspace without pyproject.toml or package_manager parameter
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify behavior: should prompt user and show completion message
        mock_interactive_functions['is_interactive'].assert_called_once()
        mock_interactive_functions['prompt_pyproject'].assert_called_once()
        mock_interactive_functions['display'].assert_called_once()

        # Verify no pyproject.toml was created
        assert not (workspace_path / "pyproject.toml").exists()


def test_create_workspace_non_interactive_no_pyproject(mock_interactive_functions):
    """Test workspace creation in non-interactive mode without pyproject.toml."""
    # Setup mocks
    mock_interactive_functions['is_interactive'].return_value = False

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create workspace without pyproject.toml or package_manager parameter
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify behavior: should show completion message, no prompting
        mock_interactive_functions['is_interactive'].assert_called_once()
        mock_interactive_functions['display'].assert_called_once()

        # Verify no pyproject.toml was created
        assert not (workspace_path / "pyproject.toml").exists()


def test_create_workspace_with_explicit_package_manager_skips_prompting(mock_interactive_functions):
    """Test that explicit package_manager parameter skips prompting."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing pyproject.toml
        existing_content = textwrap.dedent("""
            [project]
            name = "test-project"
            version = "0.1.0"
        """).strip()
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # Create workspace with explicit package_manager
        create_workspace(workspace_path, "test_namespace", "loose", package_manager="uv")

        # Verify behavior: should skip all interactive logic
        mock_interactive_functions['is_interactive'].assert_not_called()
        mock_interactive_functions['prompt_pyproject'].assert_not_called()
        mock_interactive_functions['display'].assert_not_called()

        # Verify backend was configured
        content = (workspace_path / "pyproject.toml").read_text()
        assert "hatchling" in content


def test_prompt_for_pyproject_creation_and_configuration_yes(mock_user_input):
    """Test prompting for pyproject creation when user says yes."""
    # Mock inputs: yes to create, then uv
    mock_user_input.side_effect = ["y", "uv"]

    result = prompt_for_pyproject_creation_and_configuration("test-project")

    assert result == PackageManagerEnum.UV
    assert mock_user_input.call_count == 2


def test_prompt_for_pyproject_creation_and_configuration_no(mock_user_input):
    """Test prompting for pyproject creation when user says no."""
    mock_user_input.return_value = "n"

    result = prompt_for_pyproject_creation_and_configuration("test-project")

    assert result is None
    assert mock_user_input.call_count == 1


# Package Manager Auto-Detection Tests

def test_detect_package_manager_uv_lock(tmp_path):
    """Test package manager detection from uv.lock file."""
    (tmp_path / "uv.lock").write_text("# uv.lock content")

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.UV


def test_detect_package_manager_poetry_lock(tmp_path):
    """Test package manager detection from poetry.lock file."""
    (tmp_path / "poetry.lock").write_text("# poetry.lock content")

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.POETRY


def test_detect_package_manager_pdm_lock(tmp_path):
    """Test package manager detection from pdm.lock file."""
    (tmp_path / "pdm.lock").write_text("# pdm.lock content")

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.PDM


def test_detect_package_manager_multiple_locks_priority(tmp_path):
    """Test package manager detection with multiple lock files follows UV -> Poetry -> PDM priority."""
    (tmp_path / "uv.lock").write_text("# uv.lock content")
    (tmp_path / "poetry.lock").write_text("# poetry.lock content")
    (tmp_path / "pdm.lock").write_text("# pdm.lock content")

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.UV


def test_detect_package_manager_from_pyproject_poetry(tmp_path):
    """Test package manager detection from pyproject.toml backend (poetry)."""
    pyproject_content = textwrap.dedent("""
        [build-system]
        requires = ["poetry-core"]
        build-backend = "poetry.core.masonry.api"

        [project]
        name = "test-project"
        version = "0.1.0"
    """).strip()
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.POETRY


def test_detect_package_manager_from_pyproject_pdm(tmp_path):
    """Test package manager detection from pyproject.toml backend (pdm)."""
    pyproject_content = textwrap.dedent("""
        [build-system]
        requires = ["pdm-backend"]
        build-backend = "pdm.backend"

        [project]
        name = "test-project"
        version = "0.1.0"
    """).strip()
    (tmp_path / "pyproject.toml").write_text(pyproject_content)

    result = detect_package_manager(tmp_path)

    assert result == PackageManagerEnum.PDM


def test_detect_package_manager_no_detection(tmp_path):
    """Test package manager detection returns None when nothing detected."""
    result = detect_package_manager(tmp_path)

    assert result is None


def test_detect_command_context_uv(monkeypatch):
    """Test command context detection from sys.argv showing uv run."""
    monkeypatch.setattr('sys.argv', ["uv", "run", "poly", "create", "workspace"])

    result = detect_command_context()

    assert result == PackageManagerEnum.UV


def test_detect_command_context_poetry(monkeypatch):
    """Test command context detection from sys.argv showing poetry run."""
    monkeypatch.setattr('sys.argv', ["poetry", "run", "poly", "create", "workspace"])

    result = detect_command_context()

    assert result == PackageManagerEnum.POETRY


def test_detect_command_context_hatch(monkeypatch):
    """Test command context detection from sys.argv showing hatch run."""
    monkeypatch.setattr('sys.argv', ["hatch", "run", "poly", "create", "workspace"])

    result = detect_command_context()

    assert result == PackageManagerEnum.HATCH


def test_detect_command_context_no_context(monkeypatch):
    """Test command context detection returns None when no context detected."""
    monkeypatch.setattr('sys.argv', ["poly", "create", "workspace"])

    result = detect_command_context()

    assert result is None


def test_prompt_for_package_manager_configuration_with_detection_detected_accept(tmp_path, mock_user_input):
    """Test prompting with detected package manager when user accepts."""
    (tmp_path / "uv.lock").write_text("# uv.lock content")

    mock_user_input.return_value = ""

    result = prompt_for_package_manager_configuration_with_detection(tmp_path)

    assert result == PackageManagerEnum.UV
    assert mock_user_input.call_count == 1


def test_prompt_for_package_manager_configuration_with_detection_detected_decline(tmp_path, mock_user_input):
    """Test prompting with detected package manager when user declines and chooses manually."""
    (tmp_path / "uv.lock").write_text("# uv.lock content")

    mock_user_input.side_effect = ["n", "poetry"]

    result = prompt_for_package_manager_configuration_with_detection(tmp_path)

    assert result == PackageManagerEnum.POETRY
    assert mock_user_input.call_count == 2


def test_prompt_for_package_manager_configuration_with_detection_no_detection(tmp_path, mock_user_input):
    """Test prompting falls back to comprehensive prompt when no detection occurs."""
    mock_user_input.side_effect = ["y", "uv"]

    result = prompt_for_package_manager_configuration_with_detection(tmp_path)

    assert result == PackageManagerEnum.UV
    assert mock_user_input.call_count == 2