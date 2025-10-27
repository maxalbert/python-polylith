import tempfile
import textwrap
from pathlib import Path

import pytest
import tomlkit
from polylith.workspace.package_managers import PackageManagerEnum
from polylith.workspace.build_backends import BuildBackendEnum
from polylith.workspace.create import detect_existing_build_backend
from polylith.workspace.package_manager_factory import get_package_manager
from polylith.workspace.build_backend_factory import get_build_backend


@pytest.fixture(scope="module")
def package_managers():
    """Create all package manager instances for reuse across tests."""
    return {
        'uv': get_package_manager(PackageManagerEnum.UV),
        'hatch': get_package_manager(PackageManagerEnum.HATCH),
        'poetry': get_package_manager(PackageManagerEnum.POETRY),
        'pdm': get_package_manager(PackageManagerEnum.PDM),
    }


def test_package_manager_to_build_backend_mapping(package_managers):
    """Test package manager to build backend mapping."""
    assert package_managers['uv'].get_build_backend().get_identifier() == "hatchling"
    assert package_managers['hatch'].get_build_backend().get_identifier() == "hatchling"
    assert package_managers['poetry'].get_build_backend().get_identifier() == "poetry-core"
    assert package_managers['pdm'].get_build_backend().get_identifier() == "pdm-backend"


def test_create_hatchling_backend_config():
    """Test generating hatchling backend configuration."""
    backend = get_build_backend(BuildBackendEnum.HATCHLING)
    config = backend.generate_config()

    # Check build-system section
    assert "build-system" in config
    build_system = config["build-system"]
    assert "hatchling" in build_system["requires"]
    assert build_system["build-backend"] == "hatchling.build"

    # Check tool.hatch.build section
    assert "tool" in config
    assert "hatch" in config["tool"]
    assert "build" in config["tool"]["hatch"]

    hatch_build = config["tool"]["hatch"]["build"]
    expected_dirs = ["components", "bases", "development", "."]
    assert hatch_build["dev-mode-dirs"] == expected_dirs


def test_detect_existing_build_backend_none():
    """Test detecting backend when no pyproject.toml exists."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        backend = detect_existing_build_backend(workspace_path)

        assert backend.get_enum() == BuildBackendEnum.NONE


def test_detect_existing_build_backend_poetry():
    """Test detecting poetry backend."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        pyproject_content = textwrap.dedent("""
            [build-system]
            requires = ["poetry-core>=1.0.0"]
            build-backend = "poetry.core.masonry.api"

            [tool.poetry]
            name = "test-project"
            version = "0.1.0"
        """).strip()
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        backend = detect_existing_build_backend(workspace_path)

        assert backend.get_enum() == BuildBackendEnum.POETRY_CORE


def test_detect_existing_build_backend_hatchling():
    """Test detecting hatchling backend."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        pyproject_content = """
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build]
dev-mode-dirs = ["components", "bases", "development", "."]
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        backend = detect_existing_build_backend(workspace_path)

        assert backend.get_enum() == BuildBackendEnum.HATCHLING


def test_detect_existing_build_backend_unsupported():
    """Test detecting unsupported backend."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        pyproject_content = """
[build-system]
requires = ["some-unknown-backend"]
build-backend = "unknown.backend.api"
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        backend = detect_existing_build_backend(workspace_path)

        assert backend.get_enum() == BuildBackendEnum.UNSUPPORTED


def test_detect_existing_build_backend_missing_build_system():
    """Test detecting when build-system section is missing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        pyproject_content = """
[project]
name = "test-project"
version = "0.1.0"
"""
        (workspace_path / "pyproject.toml").write_text(pyproject_content)

        backend = detect_existing_build_backend(workspace_path)

        assert backend.get_enum() == BuildBackendEnum.NONE


def test_detect_existing_build_backend_invalid_toml():
    """Test handling of invalid TOML syntax."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Invalid TOML syntax
        invalid_toml = """
[build-system
requires = ["poetry-core>=1.0.0"]  # Missing closing bracket
"""
        (workspace_path / "pyproject.toml").write_text(invalid_toml)

        with pytest.raises(ValueError, match="Invalid TOML syntax"):
            detect_existing_build_backend(workspace_path)


def test_merge_backend_config_into_existing_pyproject():
    """Test merging backend config into existing pyproject.toml."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing pyproject.toml with project info
        existing_content = """
[project]
name = "test-project"
version = "0.1.0"
description = "A test project"

[project.dependencies]
requests = "*"
"""
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # Merge uv backend config using PackageManager
        pm = get_package_manager(PackageManagerEnum.UV)
        pm.merge_backend_into_pyproject(workspace_path)

        # Verify the result
        content = tomlkit.loads((workspace_path / "pyproject.toml").read_text())

        # Original content should be preserved
        assert content["project"]["name"] == "test-project"
        assert content["project"]["version"] == "0.1.0"
        assert content["project"]["dependencies"]["requests"] == "*"

        # Backend config should be added
        assert content["build-system"]["build-backend"] == "hatchling.build"
        assert "hatchling" in content["build-system"]["requires"]

        expected_dirs = ["components", "bases", "development", "."]
        assert content["tool"]["hatch"]["build"]["dev-mode-dirs"] == expected_dirs


def test_merge_backend_config_requires_existing_pyproject():
    """Test that merge fails when pyproject.toml doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Attempt to merge without existing pyproject.toml
        pm = get_package_manager(PackageManagerEnum.UV)
        with pytest.raises(ValueError, match="No pyproject.toml found"):
            pm.merge_backend_into_pyproject(workspace_path)


def test_merge_backend_config_with_conflicting_backend():
    """Test merge fails with conflicting backend configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing pyproject.toml with poetry backend
        existing_content = """
[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"

[tool.poetry]
name = "test-project"
version = "0.1.0"
"""
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # Attempt to merge conflicting uv backend
        pm = get_package_manager(PackageManagerEnum.UV)
        with pytest.raises(ValueError, match="Conflicting backend configuration"):
            pm.merge_backend_into_pyproject(workspace_path)


def test_merge_backend_config_with_unsupported_existing_backend():
    """Test merge fails with unsupported existing backend."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create existing pyproject.toml with unsupported backend
        existing_content = """
[build-system]
requires = ["unknown-backend"]
build-backend = "unknown.backend.api"
"""
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # Attempt to merge with unsupported existing backend
        pm = get_package_manager(PackageManagerEnum.UV)
        with pytest.raises(ValueError, match="Conflicting backend configuration"):
            pm.merge_backend_into_pyproject(workspace_path)


def test_merge_backend_config_idempotent():
    """Test that merging same backend config is idempotent."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)

        # Create minimal existing pyproject.toml
        existing_content = """
[project]
name = "test-project"
version = "0.1.0"
"""
        (workspace_path / "pyproject.toml").write_text(existing_content)

        # First merge
        pm = get_package_manager(PackageManagerEnum.UV)
        pm.merge_backend_into_pyproject(workspace_path)
        first_content = (workspace_path / "pyproject.toml").read_text()

        # Second merge (should be no-op)
        pm.merge_backend_into_pyproject(workspace_path)
        second_content = (workspace_path / "pyproject.toml").read_text()

        assert first_content == second_content


def test_get_package_manager_invalid_string():
    """Test that get_package_manager fails for invalid package manager strings."""
    # Test with invalid package manager string
    with pytest.raises(ValueError, match="Unsupported package manager"):
        get_package_manager("invalid_manager")


# Tests for individual PackageManager protocol methods


def test_package_manager_get_init_command(package_managers):
    """Test get_init_command method for all package managers."""
    project_name = "my-test-project"

    assert package_managers['uv'].get_init_command(project_name) == "uv init --name my-test-project"
    assert package_managers['hatch'].get_init_command(project_name) == "hatch new --cli my-test-project"
    assert package_managers['poetry'].get_init_command(project_name) == "poetry init --name my-test-project"
    assert package_managers['pdm'].get_init_command(project_name) == "pdm init --name my-test-project"


def test_package_manager_get_identifier(package_managers):
    """Test get_identifier method for all package managers."""
    assert package_managers['uv'].get_identifier() == "uv"
    assert package_managers['hatch'].get_identifier() == "hatch"
    assert package_managers['poetry'].get_identifier() == "poetry"
    assert package_managers['pdm'].get_identifier() == "pdm"


def test_package_manager_get_display_name(package_managers):
    """Test get_display_name method for all package managers."""
    assert package_managers['uv'].get_display_name() == "UV"
    assert package_managers['hatch'].get_display_name() == "Hatch"
    assert package_managers['poetry'].get_display_name() == "Poetry"
    assert package_managers['pdm'].get_display_name() == "PDM"


def test_package_manager_generate_missing_pyproject_error(package_managers):
    """Test generate_missing_pyproject_error method for all package managers."""
    test_path = Path("/test/workspace")
    namespace = "test-workspace"

    uv_error = package_managers['uv'].generate_missing_pyproject_error(test_path, namespace)
    hatch_error = package_managers['hatch'].generate_missing_pyproject_error(test_path, namespace)
    poetry_error = package_managers['poetry'].generate_missing_pyproject_error(test_path, namespace)
    pdm_error = package_managers['pdm'].generate_missing_pyproject_error(test_path, namespace)

    # First verify these are actual error messages starting with the expected error text
    assert uv_error.startswith("No pyproject.toml found at")
    assert hatch_error.startswith("No pyproject.toml found at")
    assert poetry_error.startswith("No pyproject.toml found at")
    assert pdm_error.startswith("No pyproject.toml found at")

    # Check the full path is mentioned correctly
    expected_path_text = f"No pyproject.toml found at {test_path / 'pyproject.toml'}"
    assert expected_path_text in uv_error
    assert expected_path_text in hatch_error
    assert expected_path_text in poetry_error
    assert expected_path_text in pdm_error

    # Check that the init commands appear in the expected context
    project_name = test_path.name
    assert f"Run `uv init --name {project_name}` first to create the project configuration." in uv_error
    assert f"Run `hatch new --cli {project_name}` first to create the project configuration." in hatch_error
    assert f"Run `poetry init --name {project_name}` first to create the project configuration." in poetry_error
    assert f"Run `pdm init --name {project_name}` first to create the project configuration." in pdm_error


def test_package_manager_generate_conflicting_backend_error(package_managers):
    """Test generate_conflicting_backend_error method for all package managers."""
    test_path = Path("/test/workspace")

    # Create a mock existing backend (Poetry) that conflicts with UV/Hatch
    existing_backend = get_build_backend(BuildBackendEnum.POETRY_CORE)

    uv_error = package_managers['uv'].generate_conflicting_backend_error(existing_backend, test_path)
    hatch_error = package_managers['hatch'].generate_conflicting_backend_error(existing_backend, test_path)

    # First verify these are actual error messages starting with the expected error text
    assert uv_error.startswith("Conflicting backend configuration in")
    assert hatch_error.startswith("Conflicting backend configuration in")

    # Check the full path context is mentioned correctly
    expected_path_context = f"Conflicting backend configuration in {test_path / 'pyproject.toml'}: existing poetry-core"
    assert expected_path_context in uv_error
    assert expected_path_context in hatch_error

    # Check the specific conflict descriptions are correct
    assert "existing poetry-core, but UV requires hatchling" in uv_error
    assert "existing poetry-core, but Hatch requires hatchling" in hatch_error

    # Check both errors end with the expected resolution message
    assert uv_error.endswith("Manual configuration required.")
    assert hatch_error.endswith("Manual configuration required.")


def test_package_manager_get_init_command_args(package_managers):
    """Test package managers return correct init command args."""
    uv_args = package_managers['uv'].get_init_command_args("test-project")
    hatch_args = package_managers['hatch'].get_init_command_args("test-project")
    poetry_args = package_managers['poetry'].get_init_command_args("test-project")
    pdm_args = package_managers['pdm'].get_init_command_args("test-project")

    assert uv_args == ["uv", "init", "--bare", "--name", "test-project"]
    assert hatch_args is None
    assert poetry_args == ["poetry", "init", "--name", "test-project", "--version", "0.1.0", "--no-interaction"]
    assert pdm_args == ["pdm", "init", "--name", "test-project", "--version", "0.1.0", "--no-interaction"]


def test_package_manager_get_init_command_description(package_managers):
    """Test package managers return correct init command descriptions."""
    uv_desc = package_managers['uv'].get_init_command_description("test-project")
    hatch_desc = package_managers['hatch'].get_init_command_description("test-project")
    poetry_desc = package_managers['poetry'].get_init_command_description("test-project")
    pdm_desc = package_managers['pdm'].get_init_command_description("test-project")

    assert uv_desc == "uv init --bare --name test-project"
    assert hatch_desc == "basic template (no minimal init available)"
    assert poetry_desc == "poetry init --name test-project --version 0.1.0 --no-interaction"
    assert pdm_desc == "pdm init --name test-project --version 0.1.0 --no-interaction"


def test_package_manager_create_pyproject_template_fallback(package_managers):
    """Test creating pyproject.toml using template fallback (via hatch)."""
    import tempfile
    import textwrap
    from pathlib import Path

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        package_managers['hatch'].create_pyproject_toml(temp_path, "test-project")

        expected_content = textwrap.dedent("""
        [project]
        name = "test-project"
        version = "0.1.0"
        """).strip()

        actual_content = (temp_path / "pyproject.toml").read_text().strip()
        assert actual_content == expected_content