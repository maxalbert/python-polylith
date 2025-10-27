"""Package manager protocol definitions and implementations."""

from typing import Protocol
from pathlib import Path
from enum import Enum

from polylith.workspace.build_backends import (
    BuildBackend,
    HatchlingBackend,
    PoetryCoreBackend,
    PdmBackend,
)
from polylith.workspace.pyproject_manager import PyProjectTOMLManager


class PackageManagerEnum(Enum):
    """Enum representing user-facing package managers."""
    UV = "uv"
    HATCH = "hatch"
    POETRY = "poetry"
    PDM = "pdm"

    @classmethod
    def supported_values_string(cls) -> str:
        """Return a comma-separated string of supported package manager values."""
        return ", ".join(pm.value for pm in cls)


class PackageManager(Protocol):
    """Protocol for package manager implementations."""

    def get_init_command(self, project_name: str) -> str:
        """Return command to initialize a new project."""
        ...

    def get_build_backend(self) -> BuildBackend:
        """Return the associated build backend instance."""
        ...

    def get_identifier(self) -> str:
        """Return the package manager identifier (e.g., 'uv', 'hatch')."""
        ...

    def get_display_name(self) -> str:
        """Return human-friendly display name for error messages."""
        ...

    def merge_backend_into_pyproject(self, path: Path) -> None:
        """Merge this package manager's backend config into pyproject.toml."""
        ...

    def generate_missing_pyproject_error(self, path: Path, namespace: str) -> str:
        """Generate helpful error for missing pyproject.toml."""
        ...

    def generate_conflicting_backend_error(self, existing: BuildBackend, path: Path) -> str:
        """Generate helpful error for conflicting backends."""
        ...


class PackageManagerMixin:
    """Mixin providing default implementations for PackageManager protocol methods."""

    def merge_backend_into_pyproject(self, path: Path) -> None:
        """Merge this package manager's backend config into pyproject.toml."""
        pyproject_path = path / "pyproject.toml"
        manager = PyProjectTOMLManager.from_file(pyproject_path)

        if manager.is_empty():
            raise ValueError(self.generate_missing_pyproject_error(path, path.name))

        try:
            updated_manager = manager.merge_backend_if_compatible(self.get_build_backend())
            updated_manager.write_content(pyproject_path)
        except ValueError as e:
            if "Incompatible backends" in str(e):
                existing_backend = manager.detect_build_backend()
                raise ValueError(self.generate_conflicting_backend_error(existing_backend, path)) from e
            raise

    def generate_missing_pyproject_error(self, path: Path, namespace: str) -> str:
        """Generate helpful error for missing pyproject.toml."""
        project_name = path.name
        init_cmd = self.get_init_command(project_name)
        return f"No pyproject.toml found at {path / 'pyproject.toml'}. Run `{init_cmd}` first to create the project configuration."

    def generate_conflicting_backend_error(self, existing: BuildBackend, path: Path) -> str:
        """Generate helpful error for conflicting backends."""
        my_backend = self.get_build_backend()
        return f"Conflicting backend configuration in {path / 'pyproject.toml'}: existing {existing.get_identifier()}, but {self.get_display_name()} requires {my_backend.get_identifier()}. Manual configuration required."


# Concrete PackageManager Implementations

class UvPackageManager(PackageManagerMixin):
    """UV package manager implementation."""

    def get_init_command(self, project_name: str) -> str:
        return f"uv init --name {project_name}"

    def get_build_backend(self) -> BuildBackend:
        # TODO: Future flexibility - accept backend as constructor parameter
        return HatchlingBackend()

    def get_identifier(self) -> str:
        return "uv"

    def get_display_name(self) -> str:
        return "UV"


class HatchPackageManager(PackageManagerMixin):
    """Hatch package manager implementation."""

    def get_init_command(self, project_name: str) -> str:
        return f"hatch new --cli {project_name}"

    def get_build_backend(self) -> BuildBackend:
        # TODO: Future flexibility - accept backend as constructor parameter
        return HatchlingBackend()

    def get_identifier(self) -> str:
        return "hatch"

    def get_display_name(self) -> str:
        return "Hatch"


class PoetryPackageManager(PackageManagerMixin):
    """Poetry package manager implementation."""

    def get_init_command(self, project_name: str) -> str:
        return f"poetry init --name {project_name}"

    def get_build_backend(self) -> BuildBackend:
        # TODO: Future flexibility - accept backend as constructor parameter
        return PoetryCoreBackend()

    def get_identifier(self) -> str:
        return "poetry"

    def get_display_name(self) -> str:
        return "Poetry"


class PdmPackageManager(PackageManagerMixin):
    """PDM package manager implementation."""

    def get_init_command(self, project_name: str) -> str:
        return f"pdm init --name {project_name}"

    def get_build_backend(self) -> BuildBackend:
        # TODO: Future flexibility - accept backend as constructor parameter
        return PdmBackend()

    def get_identifier(self) -> str:
        return "pdm"

    def get_display_name(self) -> str:
        return "PDM"