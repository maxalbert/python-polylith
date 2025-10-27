import textwrap
import pytest
from typer.testing import CliRunner
from polylith.cli.create import app


@pytest.fixture
def cli_runner():
    """Fixture providing CLI runner for testing Typer applications."""
    return CliRunner()


@pytest.fixture
def in_tmp_workspace_dir(tmp_path, monkeypatch):
    """Fixture that changes to a temporary directory for workspace creation tests."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_workspace_command_without_package_manager_flag(cli_runner, in_tmp_workspace_dir):
    """Test workspace creation without --package-manager flag."""
    result = cli_runner.invoke(app, ["workspace", "--name", "test-workspace"])

    assert result.exit_code == 0
    # Verify workspace structure was created
    assert (in_tmp_workspace_dir / "workspace.toml").exists()
    assert (in_tmp_workspace_dir / "bases").exists()
    assert (in_tmp_workspace_dir / "components").exists()
    assert (in_tmp_workspace_dir / "projects").exists()


def test_workspace_command_with_package_manager_flag(cli_runner, in_tmp_workspace_dir):
    """Test workspace creation with --package-manager flag."""
    # Create a pyproject.toml for backend configuration
    pyproject_content = textwrap.dedent("""
        [project]
        name = "test-project"
        version = "0.1.0"
        """).strip()
    (in_tmp_workspace_dir / "pyproject.toml").write_text(pyproject_content)

    result = cli_runner.invoke(app, [
        "workspace",
        "--name", "test-workspace",
        "--package-manager", "uv"
    ])

    assert result.exit_code == 0
    # Verify workspace structure was created
    assert (in_tmp_workspace_dir / "workspace.toml").exists()
    # Verify backend configuration was added
    pyproject_text = (in_tmp_workspace_dir / "pyproject.toml").read_text()
    assert "hatchling" in pyproject_text


def test_workspace_command_with_package_manager_and_theme_flags(cli_runner, in_tmp_workspace_dir):
    """Test workspace creation with both --package-manager and --theme flags."""
    # Create a pyproject.toml for backend configuration
    pyproject_content = textwrap.dedent("""
        [project]
        name = "test-project"
        version = "0.1.0"
        """).strip()
    (in_tmp_workspace_dir / "pyproject.toml").write_text(pyproject_content)

    result = cli_runner.invoke(app, [
        "workspace",
        "--name", "test-workspace",
        "--theme", "loose",
        "--package-manager", "hatch"
    ])

    assert result.exit_code == 0
    # Verify workspace structure was created
    assert (in_tmp_workspace_dir / "workspace.toml").exists()
    # Verify backend configuration was added (both uv and hatch use hatchling)
    pyproject_text = (in_tmp_workspace_dir / "pyproject.toml").read_text()
    assert "hatchling" in pyproject_text


def test_workspace_command_with_invalid_package_manager(cli_runner, in_tmp_workspace_dir):
    """Test workspace creation with invalid --package-manager value."""
    result = cli_runner.invoke(app, [
        "workspace",
        "--name", "test-workspace",
        "--package-manager", "invalid"
    ])

    assert result.exit_code == 1
    assert "Unsupported package manager 'invalid'" in result.output
    assert "Valid options:" in result.output


def test_workspace_command_help_shows_package_manager_option(cli_runner):
    """Test that --help shows the --package-manager option."""
    result = cli_runner.invoke(app, ["workspace", "--help"])

    assert result.exit_code == 0
    assert "--package-manager" in result.output