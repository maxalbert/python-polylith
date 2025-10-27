import tempfile
import textwrap
from pathlib import Path
from unittest.mock import Mock

import pytest
from polylith.workspace.create import (
    create_workspace,
    is_interactive_environment,
    prompt_for_package_manager_configuration,
    display_setup_completion_message,
    PackageManagerEnum,
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

    mocks['prompt'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.prompt_for_package_manager_configuration', mocks['prompt'])

    mocks['display'] = Mock()
    monkeypatch.setattr('polylith.workspace.create.display_setup_completion_message', mocks['display'])

    return mocks


def test_is_interactive_environment_true(mock_tty_true):
    """Test interactive environment detection when TTY is available."""
    assert is_interactive_environment() is True


def test_is_interactive_environment_false(mock_tty_false):
    """Test interactive environment detection when TTY is not available."""
    assert is_interactive_environment() is False


def test_prompt_for_package_manager_configuration_yes(mock_user_input):
    """Test prompting user who chooses to configure package manager."""
    mock_user_input.side_effect = ["y", "uv"]

    result = prompt_for_package_manager_configuration()

    assert result == PackageManagerEnum.UV
    assert mock_user_input.call_count == 2


def test_prompt_for_package_manager_configuration_no(mock_user_input):
    """Test prompting user who declines to configure package manager."""
    mock_user_input.side_effect = ["n"]

    result = prompt_for_package_manager_configuration()

    assert result is None
    assert mock_user_input.call_count == 1


def test_prompt_for_package_manager_configuration_invalid_choice(mock_user_input):
    """Test prompting handles invalid package manager choices."""
    mock_user_input.side_effect = ["y", "invalid", "poetry"]

    result = prompt_for_package_manager_configuration()

    assert result == PackageManagerEnum.POETRY
    assert mock_user_input.call_count == 3


def test_prompt_for_package_manager_configuration_case_insensitive(mock_user_input):
    """Test prompting handles case-insensitive input."""
    mock_user_input.side_effect = ["Y", "UV"]

    result = prompt_for_package_manager_configuration()

    assert result == PackageManagerEnum.UV


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
    mock_interactive_functions['prompt'].return_value = PackageManagerEnum.UV

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

        # Verify behavior: should prompt user and configure backend
        mock_interactive_functions['is_interactive'].assert_called_once()
        mock_interactive_functions['prompt'].assert_called_once()
        mock_interactive_functions['display'].assert_not_called()  # No completion message needed

        # Verify backend was configured
        content = (workspace_path / "pyproject.toml").read_text()
        assert "hatchling" in content


def test_create_workspace_interactive_no_pyproject_user_declines(mock_interactive_functions):
    """Test workspace creation when user declines to configure package manager."""
    # Setup mocks
    mock_interactive_functions['is_interactive'].return_value = True
    mock_interactive_functions['prompt'].return_value = None  # User declines

    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create workspace without pyproject.toml or package_manager parameter
        create_workspace(workspace_path, "test_namespace", "loose")

        # Verify behavior: should prompt user and show completion message
        mock_interactive_functions['is_interactive'].assert_called_once()
        mock_interactive_functions['prompt'].assert_called_once()
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
        mock_interactive_functions['prompt'].assert_not_called()
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
        mock_interactive_functions['prompt'].assert_not_called()
        mock_interactive_functions['display'].assert_not_called()

        # Verify backend was configured
        content = (workspace_path / "pyproject.toml").read_text()
        assert "hatchling" in content