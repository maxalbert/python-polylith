"""Package manager protocol definitions and implementations."""

from typing import Protocol
from pathlib import Path
from enum import Enum
import subprocess
import tomlkit

from polylith.workspace.build_backends import (
    BuildBackend,
    HatchlingBackend,
    PoetryCoreBackend,
    PdmBackend,
)
from polylith.workspace.pyproject_manager import PyProjectTOMLManager


class PyProjectTOMLCreationError(Exception):
    """Exception raised when pyproject.toml creation fails."""
    pass


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

    def get_init_command_args(self, project_name: str) -> list[str] | None:
        """Return command args for creating pyproject.toml, or None if not supported."""
        ...

    def create_pyproject_toml(self, path: Path, project_name: str) -> None:
        """Create pyproject.toml using package manager's native tooling or template fallback."""
        ...

    def get_init_command_description(self, project_name: str) -> str:
        """Return description of how pyproject.toml would be created."""
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

    def create_pyproject_toml(self, path: Path, project_name: str) -> None:
        """Create pyproject.toml using package manager's native tooling or template fallback."""
        command_args = self.get_init_command_args(project_name)
        if command_args is None:
            self._create_pyproject_toml_template(path, project_name)
        else:
            self._run_native_init_command(command_args, path)

    def get_init_command_description(self, project_name: str) -> str:
        """Return description of how pyproject.toml would be created."""
        command_args = self.get_init_command_args(project_name)
        if command_args is None:
            return "basic template (no minimal init available)"
        return " ".join(command_args)

    def _run_native_init_command(self, command_args: list[str], path: Path) -> None:
        """Run native package manager init command."""
        try:
            result = subprocess.run(
                command_args,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                raise PyProjectTOMLCreationError(f"Command failed: {' '.join(command_args)}\n{result.stderr}")
        except subprocess.TimeoutExpired as e:
            raise PyProjectTOMLCreationError(f"Command timed out: {' '.join(command_args)}") from e
        except FileNotFoundError as e:
            raise PyProjectTOMLCreationError(f"Command not found: {command_args[0]}") from e
        except subprocess.SubprocessError as e:
            raise PyProjectTOMLCreationError(f"Command failed: {' '.join(command_args)}") from e

    def _create_pyproject_toml_template(self, path: Path, project_name: str) -> None:
        """Create basic pyproject.toml template (without backend config)."""
        basic_content = {
            "project": {
                "name": project_name,
                "version": "0.1.0",
            }
        }

        pyproject_path = path / "pyproject.toml"
        with pyproject_path.open("w", encoding="utf-8") as f:
            f.write(tomlkit.dumps(basic_content))


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

    def get_init_command_args(self, project_name: str) -> list[str] | None:
        """Return UV init command args."""
        return ["uv", "init", "--bare", "--name", project_name]


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

    def get_init_command_args(self, project_name: str) -> list[str] | None:
        """Return None since Hatch doesn't support minimal init."""
        return None


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

    def get_init_command_args(self, project_name: str) -> list[str] | None:
        """Return Poetry init command args."""
        return ["poetry", "init", "--name", project_name, "--version", "0.1.0", "--no-interaction"]


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

    def get_init_command_args(self, project_name: str) -> list[str] | None:
        """Return PDM init command args."""
        return ["pdm", "init", "--name", project_name, "--version", "0.1.0", "--no-interaction"]