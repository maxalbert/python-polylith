"""
Integration tests documenting manual workspace setup requirements.

These tests serve three purposes:
1. Document current workflow (manual pyproject.toml configuration)
2. Specify what automation should achieve (future work)
3. Provide regression tests when automation is added
"""
import subprocess
from pathlib import Path

import pytest
import tomlkit
from polylith.workspace.create import create_workspace


@pytest.mark.documentation
def test_uv_workspace_requires_manual_pyproject_configuration(tmp_path):
    """
    Documents the current manual steps required to set up a Polylith
    workspace with uv as the package manager.

    Current process (per docs at https://davidvujic.github.io/python-polylith-docs/setup/#uv):
    1. User initializes project with: uv init --name my-app
    2. User runs: poly create workspace --name example-workspace
    3. User must manually edit pyproject.toml to add:
       - build-system with hatchling
       - tool.hatch.build.dev-mode-dirs = ["components", "bases"]

    Future enhancement: Automate step 3 with:
    poly create workspace --name example-workspace --package-manager uv
    """
    # Step 1: Initialize a uv project (creates basic pyproject.toml)
    project_dir = tmp_path / "my-app"
    project_dir.mkdir()

    result = subprocess.run(
        ["uv", "init", "--bare", "--name", "my-app"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"uv init failed: {result.stderr}"

    # Verify uv created pyproject.toml with basic structure
    pyproject_path = project_dir / "pyproject.toml"
    assert pyproject_path.exists(), "uv init should create pyproject.toml"

    config_before = tomlkit.load(pyproject_path.open())
    assert "project" in config_before, "uv init should create [project] section"
    assert "my-app" == config_before["project"]["name"], "python project name should be 'my-app'"

    # Step 2: Create Polylith workspace structure
    workspace_namespace = "example-workspace"
    create_workspace(project_dir, workspace_namespace, theme="tdd")

    # Verify Polylith workspace structure was created
    assert (project_dir / "components").exists(), "components/ should exist"
    assert (project_dir / "bases").exists(), "bases/ should exist"
    assert (project_dir / "projects").exists(), "projects/ should exist"
    assert (project_dir / "workspace.toml").exists(), "workspace.toml should exist"

    # Step 3: Document what's MISSING - Polylith-specific configuration for uv
    config_after = tomlkit.load(pyproject_path.open())

    # Document: build-system is missing or not configured for hatchling
    has_hatchling = (
        "build-system" in config_after
        and config_after["build-system"].get("build-backend") == "hatchling.build"
    )
    assert not has_hatchling, \
        "Build backend should not be hatchling yet (requires manual configuration)"

    # Document: hatch dev-mode-dirs configuration is missing
    has_dev_mode_dirs = (
        "tool" in config_after
        and "hatch" in config_after.get("tool", {})
        and "build" in config_after.get("tool", {}).get("hatch", {})
        and "dev-mode-dirs" in config_after.get("tool", {}).get("hatch", {}).get("build", {})
    )
    assert not has_dev_mode_dirs, \
        "Hatch dev-mode-dirs should not be configured yet (requires manual configuration)"

    # Step 4: Document the required manual configuration
    # This is what users must currently add by hand
    required_config_additions = {
        "build-system": {
            "requires": ["hatchling"],
            "build-backend": "hatchling.build",
        },
        "tool": {
            "hatch": {
                "build": {
                    "dev-mode-dirs": ["components", "bases"],
                }
            }
        },
    }

    # Step 5: Simulate manual editing
    # (Future: this should happen automatically with --package-manager uv)
    config = tomlkit.load(pyproject_path.open())

    # User manually adds/replaces build-system
    config["build-system"] = required_config_additions["build-system"]

    # User manually adds hatch configuration
    if "tool" not in config:
        config["tool"] = tomlkit.table()
    config["tool"]["hatch"] = required_config_additions["tool"]["hatch"]

    # Write the manually-updated configuration
    with pyproject_path.open("w") as f:
        f.write(tomlkit.dumps(config))

    # Step 6: Verify the manually-configured workspace is now properly set up
    config_final = tomlkit.load(pyproject_path.open())

    assert config_final["build-system"]["build-backend"] == "hatchling.build", \
        "After manual configuration, build backend should be hatchling"
    assert config_final["tool"]["hatch"]["build"]["dev-mode-dirs"] == ["components", "bases"], \
        "After manual configuration, dev-mode-dirs should be set for Polylith"
