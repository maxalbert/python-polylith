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
from polylith.workspace.package_managers import PackageManagerEnum, PyProjectTOMLCreationError
from polylith.libs.lock_files import find_lock_files

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


def _prompt_for_package_manager_choice() -> PackageManagerEnum:
    """Prompt user to choose a package manager."""
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



def prompt_for_pyproject_creation_and_configuration(project_name: str) -> Optional[PackageManagerEnum]:
    """Prompt user to create pyproject.toml and configure package manager."""
    print("No pyproject.toml found.")
    print("")
    print("Would you like to create pyproject.toml and configure it for Polylith?")
    print("")
    print("pyproject.toml will be created using your package manager's native command when possible, otherwise from a basic template.")
    print("")
    print("Package Manager    Native Init Command")
    print("-----------------  -----------------------------------------------")

    # Show available options with their commands
    for pm_enum in PackageManagerEnum:
        pm = get_package_manager(pm_enum)
        description = pm.get_init_command_description(project_name)
        print(f"{pm_enum.value:<17}  {description}")

    print("")
    print("Polylith configuration adds build system settings and dev-mode-dirs for local development.")
    print("")

    while True:
        response = input("Proceed? (y/n): ").strip().lower()
        if response in ["y", "yes"]:
            break
        elif response in ["n", "no"]:
            return None
        # Invalid response, loop will continue

    return _prompt_for_package_manager_choice()


def display_setup_completion_message() -> None:
    """Display helpful completion message for manual setup."""
    print("Workspace created successfully!")
    print("To complete setup, either:")
    print("1. Configure pyproject.toml manually (see: https://davidvujic.github.io/python-polylith-docs/setup/)")
    print("2. Re-run with: poly create workspace --package-manager uv")


def detect_package_manager(path: Path) -> Optional[PackageManagerEnum]:
    """Auto-detect package manager from project files and context."""
    # Priority 1: Check lock files (can distinguish UV from Hatch)
    lock_files = find_lock_files(path)

    if "uv.lock" in lock_files:
        return PackageManagerEnum.UV
    elif "poetry.lock" in lock_files:
        return PackageManagerEnum.POETRY
    elif "pdm.lock" in lock_files:
        return PackageManagerEnum.PDM

    # Priority 2: Check pyproject.toml backend hints (lower priority)
    pyproject_path = path / "pyproject.toml"
    if pyproject_path.exists():
        try:
            manager = PyProjectTOMLManager.from_file(pyproject_path)
            backend = manager.detect_build_backend()
            if backend.get_identifier() == "poetry-core":
                return PackageManagerEnum.POETRY
            elif backend.get_identifier() == "pdm-backend":
                return PackageManagerEnum.PDM
            # Note: hatchling is used by both UV and Hatch, can't distinguish
            # We rely on command context detection or lock files for this
        except Exception:
            pass

    return None


def detect_command_context() -> Optional[PackageManagerEnum]:
    """Detect package manager from command context (sys.argv)."""
    if len(sys.argv) >= 2:
        if sys.argv[0] == "uv" and sys.argv[1] == "run":
            return PackageManagerEnum.UV
        elif sys.argv[0] == "poetry" and sys.argv[1] == "run":
            return PackageManagerEnum.POETRY
        elif sys.argv[0] == "pdm" and sys.argv[1] == "run":
            return PackageManagerEnum.PDM
        elif sys.argv[0] == "hatch" and sys.argv[1] == "run":
            return PackageManagerEnum.HATCH

    return None


def prompt_for_package_manager_configuration_with_detection(path: Path) -> Optional[PackageManagerEnum]:
    """Prompt with auto-detection and better context."""
    # Try command context first (highest priority)
    detected = detect_command_context()
    if not detected:
        detected = detect_package_manager(path)

    if detected:
        print(f"Polylith workspace requires package manager configuration in pyproject.toml.")
        print(f"Detected: {detected.value.upper()} package manager")

        while True:
            response = input(f"Configure pyproject.toml for Polylith with {detected.value.upper()}? (Y/n): ").strip().lower()
            if response in ["y", "yes", ""]:
                return detected
            elif response in ["n", "no"]:
                return _prompt_for_package_manager_choice()
    else:
        return prompt_for_pyproject_creation_and_configuration(path.name)


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
                # Existing pyproject.toml - use auto-detection prompting
                chosen_pm = prompt_for_package_manager_configuration_with_detection(path)
                if chosen_pm:
                    pm = get_package_manager(chosen_pm)
                    pm.merge_backend_into_pyproject(path)
                else:
                    # If user declines (chosen_pm is None), do nothing
                    pass
            else:
                # No pyproject.toml - prompt for creation and configuration
                chosen_pm = prompt_for_pyproject_creation_and_configuration(path.name)
                if chosen_pm:
                    try:
                        pm = get_package_manager(chosen_pm)
                        pm.create_pyproject_toml(path, path.name)
                        pm.merge_backend_into_pyproject(path)
                    except (PyProjectTOMLCreationError, ValueError) as e:
                        # Creation or configuration failed - show completion message
                        print(f"Error: {e}")
                        display_setup_completion_message()
                else:
                    # User declined - show completion message
                    display_setup_completion_message()
        else:
            # Non-interactive environment - show completion message
            display_setup_completion_message()
