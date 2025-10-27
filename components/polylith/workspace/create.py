from pathlib import Path
from enum import Enum
from typing import Optional
import sys

import tomlkit
from polylith import readme, repo
from polylith.development import create_development
from polylith.dirs import create_dir
from polylith.workspace.build_backends import BuildBackend
from polylith.workspace.pyproject_manager import PyProjectTOMLManager
from polylith.workspace.package_manager_factory import get_package_manager
from polylith.workspace.package_managers import PackageManagerEnum

class WorkspaceStateEnum(Enum):
    """Enum representing possible workspace states."""
    FRESH = "fresh"
    EXISTING_COMPLETE = "existing_complete"
    EXISTING_NO_PYPROJECT = "existing_no_pyproject"
    EXISTING_INCOMPLETE = "existing_incomplete"


def detect_existing_build_backend(path: Path) -> BuildBackend:
    """Detect existing build backend from pyproject.toml."""
    pyproject_path = path / "pyproject.toml"
    manager = PyProjectTOMLManager.from_file(pyproject_path)
    return manager.detect_build_backend()


template = """\
[tool.polylith]
namespace = "{namespace}"
git_tag_pattern = "stable-*"

[tool.polylith.structure]
theme = "{theme}"

[tool.polylith.tag.patterns]
stable = "stable-*"
release = "v[0-9]*"

[tool.polylith.resources]
brick_docs_enabled = false

[tool.polylith.test]
enabled = true
"""


def create_workspace_config(path: Path, namespace: str, theme: str) -> None:
    fullpath = path / repo.workspace_file

    # Only create if file doesn't exist
    if not fullpath.exists():
        formatted = template.format(namespace=namespace, theme=theme)
        content: dict = tomlkit.loads(formatted)

        with fullpath.open("w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(content))


def detect_workspace_state(path: Path) -> WorkspaceStateEnum:
    """Detect the current state of a workspace directory."""
    workspace_exists = (path / repo.workspace_file).exists()
    pyproject_exists = (path / "pyproject.toml").exists()

    if not workspace_exists and not pyproject_exists:
        return WorkspaceStateEnum.FRESH

    if workspace_exists and not pyproject_exists:
        return WorkspaceStateEnum.EXISTING_NO_PYPROJECT

    if workspace_exists and pyproject_exists:
        # Check if pyproject.toml has backend configuration
        try:
            content = tomlkit.loads((path / "pyproject.toml").read_text())
            build_system = content.get("build-system", {})
            hatch_config = content.get("tool", {}).get("hatch", {}).get("build", {})

            if build_system.get("build-backend") and hatch_config.get("dev-mode-dirs"):
                return WorkspaceStateEnum.EXISTING_COMPLETE
            else:
                return WorkspaceStateEnum.EXISTING_INCOMPLETE
        except Exception:
            return WorkspaceStateEnum.EXISTING_INCOMPLETE

    return WorkspaceStateEnum.FRESH


def is_interactive_environment() -> bool:
    """Detect if we're in an interactive TTY environment."""
    return sys.stdin.isatty()


def prompt_for_package_manager_configuration() -> Optional[PackageManagerEnum]:
    """Interactively prompt user for package manager configuration choice."""
    # First ask if they want to configure now
    while True:
        response = input("Would you like to configure a package manager now? (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            break
        elif response in ["n", "no"]:
            return None
        # Invalid response, loop will continue

    # Ask for package manager choice
    while True:
        print("Available package managers:")
        for pm in PackageManagerEnum:
            print(f"  - {pm.value}")

        choice = input("Choose a package manager: ").strip().lower()

        # Try to create enum instance from the choice
        try:
            return PackageManagerEnum(choice)
        except ValueError:
            # Invalid choice, loop will continue
            continue


def display_setup_completion_message() -> None:
    """Display helpful completion message for manual setup."""
    print("Workspace created successfully!")
    print("To complete setup, either:")
    print("1. Configure pyproject.toml manually (see: https://davidvujic.github.io/python-polylith-docs/setup/)")
    print("2. Re-run with: poly create workspace --package-manager uv")


def create_workspace(path: Path, namespace: str, theme: str, package_manager: Optional[str] = None) -> None:
    create_dir(path, repo.bases_dir, keep=True)
    create_dir(path, repo.components_dir, keep=True)
    create_dir(path, repo.projects_dir, keep=True)

    create_development(path, keep=True)

    create_workspace_config(path, namespace, theme)

    readme.create_workspace_readme(path, namespace)

    # Package manager configuration handling
    if package_manager:
        # Explicit package manager provided - skip all interactive logic
        try:
            pm = get_package_manager(package_manager)
            pm.merge_backend_into_pyproject(path)
        except ValueError:
            # Re-raise - factory and merge methods provide appropriate error messages
            raise
    else:
        # No explicit package manager - handle interactive logic
        pyproject_exists = (path / "pyproject.toml").exists()

        if is_interactive_environment():
            # Interactive environment - prompt user
            if pyproject_exists:
                # Existing pyproject.toml - prompt and configure if user chooses
                chosen_pm = prompt_for_package_manager_configuration()
                if chosen_pm:
                    pm = get_package_manager(chosen_pm)
                    pm.merge_backend_into_pyproject(path)
                else:
                    # If user declines (chosen_pm is None), do nothing
                    pass
            else:
                # No pyproject.toml - prompt and show completion message if user declines
                chosen_pm = prompt_for_package_manager_configuration()
                if chosen_pm:
                    # User chose a package manager but no pyproject.toml exists
                    # This would cause an error in merge_backend_config_into_pyproject
                    # But according to the tests, we should still call it and let it error
                    try:
                        pm = get_package_manager(chosen_pm)
                        pm.merge_backend_into_pyproject(path)
                    except ValueError:
                        # Expected error for missing pyproject.toml - show completion message
                        display_setup_completion_message()
                else:
                    # User declined - show completion message
                    display_setup_completion_message()
        else:
            # Non-interactive environment - show completion message
            display_setup_completion_message()
