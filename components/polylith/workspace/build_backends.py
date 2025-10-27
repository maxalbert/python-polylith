"""Build backend protocol definitions and implementations."""

from typing import Protocol
from enum import Enum


class BuildBackendEnum(Enum):
    """Enum representing technical build backends."""
    HATCHLING = "hatchling"
    POETRY_CORE = "poetry_core"
    PDM_BACKEND = "pdm"
    NONE = "none"
    UNSUPPORTED = "unsupported"


class BuildBackend(Protocol):
    """Protocol for build backend implementations."""

    def generate_config(self) -> dict:
        """Generate build system configuration for pyproject.toml."""
        ...

    def get_identifier(self) -> str:
        """Return backend identifier (e.g., 'hatchling', 'poetry-core')."""
        ...

    def get_enum(self) -> 'BuildBackendEnum':
        """Return the corresponding BuildBackendEnum value."""
        ...

    def is_compatible_with(self, other: 'BuildBackend') -> bool:
        """Check if this backend is compatible with another backend."""
        return other.get_identifier() == self.get_identifier()


# Concrete BuildBackend Implementations

class HatchlingBackend(BuildBackend):
    """Hatchling build backend implementation."""

    def generate_config(self) -> dict:
        """Generate hatchling build system configuration."""
        return {
            "build-system": {
                "requires": ["hatchling"],
                "build-backend": "hatchling.build",
            },
            "tool": {
                "hatch": {
                    "build": {
                        "dev-mode-dirs": ["components", "bases", "development", "."]
                    }
                }
            },
        }

    def get_identifier(self) -> str:
        return "hatchling"

    def get_enum(self) -> BuildBackendEnum:
        return BuildBackendEnum.HATCHLING


class PoetryCoreBackend(BuildBackend):
    """Poetry Core build backend implementation."""

    def generate_config(self) -> dict:
        """Generate poetry-core build system configuration."""
        return {
            "build-system": {
                "requires": ["poetry-core"],
                "build-backend": "poetry.core.masonry.api",
            },
            # TODO: Add Poetry-specific polylith configuration when supported
        }

    def get_identifier(self) -> str:
        return "poetry-core"

    def get_enum(self) -> BuildBackendEnum:
        return BuildBackendEnum.POETRY_CORE


class PdmBackend(BuildBackend):
    """PDM build backend implementation."""

    def generate_config(self) -> dict:
        """Generate PDM build system configuration."""
        return {
            "build-system": {
                "requires": ["pdm-backend"],
                "build-backend": "pdm.backend",
            },
            # TODO: Add PDM-specific polylith configuration when supported
        }

    def get_identifier(self) -> str:
        return "pdm-backend"

    def get_enum(self) -> BuildBackendEnum:
        return BuildBackendEnum.PDM_BACKEND


class UnsupportedBuildBackend:
    """Build backend implementation for unsupported/unknown backends."""

    def __init__(self, identifier: str):
        """Initialize with the detected backend identifier."""
        self.identifier = identifier

    def generate_config(self) -> dict:
        """Raise error for unsupported backend."""
        raise ValueError(f"Build backend '{self.identifier}' is not supported for Polylith workspaces")

    def get_identifier(self) -> str:
        return self.identifier

    def get_enum(self) -> BuildBackendEnum:
        return BuildBackendEnum.UNSUPPORTED

    def is_compatible_with(self, other: BuildBackend) -> bool:
        """Unsupported backends are never compatible."""
        return False


class NoBuildBackend:
    """Build backend implementation when no backend is detected."""

    def generate_config(self) -> dict:
        """Raise error for missing backend."""
        raise ValueError("No build backend configuration found")

    def get_identifier(self) -> str:
        return "none"

    def get_enum(self) -> BuildBackendEnum:
        return BuildBackendEnum.NONE

    def is_compatible_with(self, other: BuildBackend) -> bool:
        """No backend is never compatible."""
        return False